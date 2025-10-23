

import imaplib
from datetime import datetime, timedelta
import email
import os
import time
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv
import logging
from openai import OpenAI
from prompts import DOC_ANALYZER_PROMPT, GENERATE_INSERT_SQL_QUERY_PROMPT, tables, SYSTEM_PROMPT
import cv2
import json
from celery import Celery


logging.basicConfig(level=logging.INFO, format='[%(name)s] : %(message)s')
load_dotenv()

check_emails_logger = logging.getLogger('check_tool')
fetch_emails_logger = logging.getLogger('fetch_tool')
trigger_logging = logging.getLogger('trigger')
DB_logging = logging.getLogger('database_op')
agent_logging = logging.getLogger('agent')

server = os.getenv('SERVER')
username = os.getenv('INVOICE_MAIL_USERNAME')
password = os.getenv('INVOICE_MAIL_PASS')
db_host = os.getenv('db_host')
db_username = os.getenv('db_username')
db_password = os.getenv('db_password')
database = os.getenv('database')
openai_api_key = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=openai_api_key)


def format_date(date_obj):
    return date_obj.strftime("%d-%b-%Y")

app = Celery("main", broker="redis://localhost:6379", backend="redis://localhost:6379")

MODEL = 'gpt-4o'

try:
    db_pool = pooling.MySQLConnectionPool(
        pool_name="idp_app_connection_pool",
        pool_size=5,
        host=db_host,
        user=db_username,
        password=db_password,
        database=database
    )
    DB_logging.info("Database Connection Etablished")
except mysql.connector.Error as err:
    print(f"Error creating connection pool : {err}")
    exit()

def analyze_processed_documents(data):
    """Analyzes the data of processed from documents"""
    prompt = DOC_ANALYZER_PROMPT.format(data=data)
    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content
        
        return result.replace("```yaml", "").replace("```", "")
    except Exception as e:
        return f"Error : {e}"

def check_for_new_emails() -> str:
    """Checks email inbox for any new unseen/unread emails"""
    try:
        imap = imaplib.IMAP4_SSL(server)
        imap.login(username, password)

        status, messages = imap.select("INBOX")
        if status != 'OK':
            check_emails_logger.info("error selecting INBOX")
            exit
        
        date_since = format_date(datetime.now())
        search_query = f"UNSEEN SINCE {date_since}"
        status, unseen_emails = imap.uid("search", None, search_query)

        if status != 'OK':
            check_emails_logger.info("error searching for unseen emails")
            exit
        all_unseen_emails = unseen_emails[0].split()
        if all_unseen_emails:
            return "New Mail"
        else:
            check_emails_logger.info("No new emails found")
        
    except imaplib.IMAP4_SSL.error as e:
        print(f"[Check Tool] : An IMAP error occurred : {e}")

def get_email_content(msg):
    """
    Pasrses an email message object to extract the body and attachements
    """

    body = ""
    attachements = {}

    # check if the email is multipart
    if msg.is_multipart():
        # iterate over each part of the email
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # check is the part is the email body (plain text)
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode()
                except Exception as e:
                    return f"Error : {e}"
            elif "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    # Store the filename and it's raw data 
                    attachements[filename] = part.get_payload(decode=True)
    else:
        # if the email is not multipart, the playload is the body
        try:
            body = msg.get_payload(decode=True).decode()
        except Exception as e:
            return f"Error : {e}"
    
    return body, attachements

def fetch_emails_content():
    """Fetches the full the content of an email from text to the files attached to it"""
    try:
        imap = imaplib.IMAP4_SSL(server)
        imap.login(username, password)
        fetch_emails_logger.info("Login Successful!")

        status, messages = imap.select("INBOX")
        if status != 'OK':
            fetch_emails_logger.info("error selecting INBOX")
            exit
        
        date_since = format_date(datetime.now())
        search_query = f"UNSEEN SINCE {date_since}"
        status, unseen_emails = imap.uid("search", None, search_query)
        all_unseen_emails = unseen_emails[0].split()
        # latest_emails = all_unseen_emails[-10:]
        if all_unseen_emails:
            print(f"[fetch tool] : Found {len(all_unseen_emails)} new emails since {date_since}")
            uids_string = ','.join([uid.decode('utf-8') for uid in all_unseen_emails])
            status, fetched_data = imap.uid('fetch', uids_string, "(RFC822)")
            if status == 'OK':
                filenames = []
                for response in fetched_data:
                    if isinstance(response, tuple):

                        msg = email.message_from_bytes(response[1])
                        From = msg['From']
                        Subject = msg['Subject']
                        Date = msg['Date']
                        
                        # To get flags, we need to parse the first part of the response
                        flags = imaplib.ParseFlags(response[0])
                        
                        # call the get_email_content functin
                        body, attachements = get_email_content(msg)

                        email_content = f"From : {From}\nSubject : {Subject}\nDate : {Date}\nBody : {body}"

                        if attachements:
                            for filename, file_content in attachements.items():
                                # saving the file
                                if filename.endswith(".pdf"):
                                    filepath = os.path.join("data", filename)
                                else:
                                    filepath = os.path.join("data/images", filename)
                                with open(filepath, "wb") as f:
                                    f.write(file_content)
                                filenames.append(filename)
                if filenames:
                    return filenames
        else:
            fetch_emails_logger.info("No unseen emails found")
    except imaplib.IMAP4_SSL.error as e:
        return f"Error : {e}"

def process_documents(doc: str):
        print("Staring Process TOOL")
        """
        Processes documents and extracts the content of provided documents.
        Args:
            doc: Name of the document extracted from email.    
        """
        if not doc:
            print("No doc to be processed found")

        try:
            if doc.endswith(".pdf"):

                images = convert_from_path(f"data/{doc}", dpi=200)

                for i in range(len(images)):

                    images[i].save('data/images/page'+ str(i) + '.jpg', 'JPEG')

                    doc = 'page'+str(i)+'.jpg'
            
            image = cv2.imread(f"data/images/{doc}")

            gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            optimal_threshold, binary_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            text = pytesseract.image_to_string(binary_image)
            text = analyze_processed_documents(text)
            print(text)
            return text
        except Exception as e:
            return f"Error : {e}"

    
def save_po_to_db(sql):
    """
    Saves purchase orders to data base
    """
    try:
        conn = db_pool.get_connection()

        if not sql:
            print("Sql query empty")
        
        cursor = conn.cursor()

        cursor.execute(sql)

        if cursor:
            DB_logging.info("Data saved inot po table")
            conn.commit()
            return f"data saved successfully into po table"

    except Exception as e:
        return f"Error : {e}"
    
def update_po_status(po_number):
    print("Starting The po update tool")
    """
    Updates purcahse orders status
    """
    try:
        conn = db_pool.get_connection()

        # if not sql:
        #     print("Sql Query is empty")

        cursor = conn.cursor()

        sql = "UPDATE purchase_orders SET po_status = %s WHERE po_number = %s"

        new_status = "Approved"

        values = (new_status, po_number)

        cursor.execute(sql, values)

        conn.commit()

        DB_logging.info("po updated")

        return "po updated successfully"

    except Exception as e:
        return f"Error : {e}"

def find_po_by_number(po_number):
    print("Starting Tool find_po")
    """
    Retreives purchase order details
    """
    try:
        conn = db_pool.get_connection()
        
        cursor = conn.cursor()

        sql = "SELECT * FROM purchase_orders where po_number = %s"

        cursor.execute(sql, (po_number,))

        results = cursor.fetchall()

        print(results)

        if results:
            DB_logging.info("Po Found in db")
            return f"PO with number {po_number} found in db"
        else:
            return f"PO with number {po_number} not found in db"    
        
    except Exception as e:
        return f"Error : {e}"

def save_line_item(sql):
    """
    Saves lines items to database
    """
    try:
        conn = db_pool.get_connection()

        if not sql:
            print("Sql query empty")
        
        cursor = conn.cursor()

        cursor.execute(sql)

        if cursor:
            DB_logging.info("Data saved into line items table")
            conn.commit()
            return f"data saved successfully into line items table"

    except Exception as e:
        return f"Error : {e}"

def save_invoice_to_db(sql):
    """
    Saves invoices to data base
    """
    try:
        conn = db_pool.get_connection()

        if not sql:
            print("Sql query empty")
        
        cursor = conn.cursor()

        cursor.execute(sql)

        if cursor:
            DB_logging.info("Data saved into invoices table")
            conn.commit()
            return f"data saved successfully into invoices table"

    except Exception as e:
        return f"Error : {e}"
        

def update_invoice_status(invoice_number):
    """
    Updates invoices status
    """
    try:
        conn = db_pool.get_connection()

        # if not sql:
        #     print("Sql Query is empty")

        cursor = conn.cursor()

        sql = "UPDATE invoices SET invoice_status = %s WHERE invoice_number = %s"

        new_status = "Pending"

        values = (new_status, invoice_number)

        cursor.execute(sql, values)

        if cursor:
            print("invoice updated")
            conn.commit()
            return f"invoice updated successfully"
    
    except Exception as e:
        return f"Error : {e}"


def generate_sql_query_to_insert_data(data):

    """
    Generates sql queries to insert po's, line_items an invoices into the data base
    """

    prompt = GENERATE_INSERT_SQL_QUERY_PROMPT.format(data=data, tables=tables)
    try:
        
      response = client.chat.completions.create(
          model=MODEL,
          messages=[{"role": "user", "content": prompt}]
      )

      result = response.choices[0].message.content
      
      return result.replace("```json", "").replace("```", "")
    except Exception as e:
       return f"Error : {e}"


tools = [
    {
        "type": "function",
        "function": {
            "name": "process_documents",
            "description": "process docs and extracts their content",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc": {"type": "string", "description": "the name of the doc fetched from the email"}
                },
                "required": ["doc"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_sql_query_to_insert_data",
            "description": "generates an sql query that will insert the content of a processed doc into a an sql table",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "the result of process_documents"}
                },
                "required": ["data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_po_to_db",
            "description": "save the data of the all the docs of type purchase order",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "the result of generate_sql_query_to_insert_data"}
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_po_status",
            "description": "updates the status of a purchase order from pending to approved",
            "parameters": {
                "type": "object",
                "properties": {
                    "po_number": {"type": "string", "description": "the unique nubmer that identifies a purchase order"}
                },
                "required": ["po_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_po_by_number",
            "description": "retreives the data of a specific purchase order from the data base",
            "parameters": {
                "type": "object",
                "properties": {
                    "po_number": {"type": "string", "description": "the unique nubmer that identifies a purchase order"}
                },
                "required": ["po_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_line_item",
            "description": "saves the data of the found line items in the extracted data",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "the result of generate_sql_query_to_insert_data"}
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_invoice_to_db",
            "description": "saves the data of the all the docs of type invoice",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "the result of generate_sql_query_to_insert_data"}
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_invoice_status",
            "description": "updates the status of an invoice from pending to approved",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string", "description": "the unique nubmer that identifies an invoice"}
                },
                "required": ["invoice_number"]
            }
        }
    }
]


tool_implementation ={
    "process_documents": process_documents,
    "generate_sql_query_to_insert_data": generate_sql_query_to_insert_data,
    "save_po_to_db": save_po_to_db,
    "update_po_status": update_po_status,
    "find_po_by_number": find_po_by_number,
    "save_line_item": save_line_item,
    "save_invoice_to_db": save_invoice_to_db,
    "update_invoice_status": update_invoice_status
}
@app.task
def run_agent(messages):
    print("New Email Received")
    print(f"Running agent with messages:", messages)

    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    

    # check and system prompt
    if not any(
        isinstance(message, dict) and message.get("role") == "system" for message in messages
    ):
        system_prompt = {"role": "system", "content": SYSTEM_PROMPT}
        messages.append(system_prompt)
    
    while True:
        try:
            print("\nMaking Router Call")
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
            )   
            messages.append(response.choices[0].message)
            tool_calls = response.choices[0].message.tool_calls
            print("\nReceived reponse with tool calls:", bool(tool_calls))

            if tool_calls:
                print("\nProcessing tool calls")
                messages = handle_tool_calls(tool_calls, messages)
            else:
                print("\nNo tool calls, returning final response")
                return response.choices[0].message.content
        except Exception as e:
            return f"Error : {e}"

def handle_tool_calls(tool_calls, messages):
    for tool_call in tool_calls:
        function  = tool_implementation[tool_call.function.name]
        function_args = json.loads(tool_call.function.arguments)
        result = function(**function_args)
        messages.append({"role": "tool", "content": result, "tool_call_id": tool_call.id})
    return messages

def trigger(t=5):
    trigger_logging.info("Starting IDP(Intelligent Documet Processing) Workflow")
    while t:
        mins, secs = divmod(t, 60)
        timer = '{:2d}:{:2d}'.format(mins, secs)
        print(f"[trigger] : {timer}", end='\r')

        time.sleep(1)
        t -= 1

        if t == 0:
            trigger_logging.info("Cheking for new email")
            res = check_for_new_emails()
            if res  == "New Mail":
                filenames = fetch_emails_content()
                print("Found this much new docs :", len(filenames))
                for filename in filenames:
                    test = run_agent.delay(f"New document found start the workflow, filename : {filename}")
                    print(test)
            t = 5

if __name__ == "__main__":
    trigger()

