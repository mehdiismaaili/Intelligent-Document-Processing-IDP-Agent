
# Account Payable Documents Processing AI Agent

This is an account payable AI agent workflow that can retrieve invoices, purchase orders and receipts from an email dedicated only for account payable emails. After the workflow detects new unread emails it will retrieve the content of these emails and then send the documents to the AI agent to be processed and saved into a database.
## Technologies used :

***Programming Language :*** Python
**Python Libraries Used:**
	- imap
	- dotenv
	- pytesseract
	- pdf2image
	- mysql-connector-python
	- openai
	- opencv-python
	- celery
	- redis
**Docker**
**Redis**
**tesseract-ocr**
## How to run the workflow :
### .env file :
Create a file called .**env**  and put these in it :
- SERVER=imap.gmail.com
- INVOICE_MAIL_USERNAME=
- INVOICE_MAIL_PASS=
- db_host=localhost
- database=idp_db
- db_username=
- db_password=
- OPENAI_API_KEY=
### Imap Setup:

Here is how you can setup imap for your email that your gonna use for account payable :
**Enable IMAP in Gmail:**
    - Go to **Gmail** -> **Settings** (the gear icon ⚙️) -> **See all settings**.
    - Click the **Forwarding and POP/IMAP** tab.
    - In the "IMAP access" section, select **Enable IMAP**.
    - Click **Save Changes**.

**Create your App Password:**
    - Go to your Google Account at **[myaccount.google.com](https://myaccount.google.com/?authuser=1)**.
    - Click on **Security** in the left-hand menu.
    - Under "How you sign in to Google," click on **2-Step Verification**. You must have this enabled to create App Passwords.
    - Scroll to the bottom and click on **App passwords**.
    - When prompted, give the app a name (e.g., "Python Email Script") and click **Create**.
    - Google will generate a **16-character password**. **Copy this password immediately.** This is what you'll use in your script. Do not use your regular Gmail password.

Inside the **.env** files put the email as the value of **INVOICE_MAIL_USERNAME** and the app password as the value of **INVOICE_MAIL_PASS**
### Database Setup :

If you have mysql installed create database called **idp_db** and in it create the tables in the file **db.sql**
 Then in the **.env** file put yout database username as the value of **db_username** and your database password as the value of **db_password**.
 Now your database is all set up

### pytesseract set up:
You need to install **tesseract-ocr** so that pytesseract works.
Here it shows you how to install for both linux ans windows.
#### For Windows :
1. **Download the installer**: 
    Go to the UB Mannheim Tesseract repository and download the latest 64-bit installer (`.exe` file). 
2. **Run the installer**: 
    Execute the downloaded file and follow the on-screen instructions. 
3. **Add to system path**: 
    During installation, it's recommended to note the installation directory (e.g., `C:\Program Files\Tesseract-OCR`) and add it to your system's environment path variable. This allows you to run `tesseract` from any command prompt. 
4. **Verify installation**: 
    Open a command prompt and type `tesseract --version`. If the path is correct, the version number will be displayed. 
#### For Linux :
1. **Use the package manager**: 
	The easiest method is to use your distribution's package manager. 
2. **For Debian/Ubuntu-based systems**: 
	Open a terminal and run `sudo apt-get install tesseract-ocr`. 
3. **For other systems**: 
	The specific command will vary. For example, you can use `yum` or `dnf` for Fedora/RHEL-based systems, or `pacman` for Arch Linux. 
4. **Verify installation**: 
	Open a terminal and type `tesseract --version`. You should see the installed version number.

### OpenAI api key set up :
Go to [open_ai_platform](https://platform.openai.com/) and generate an api key, take the generated api key and put it as the value of **OPENAI_API_KEY=** in the **.env** file.


### Redis setup 
Now you need to install a few important things for redis to work on your computer.
#### Docker installation :

#### Windows 🪟

On Windows, the standard way to install Docker is using **Docker Desktop**. It requires the **Windows Subsystem for Linux version 2 (WSL 2)**.

##### 1. Enable WSL 2

First, ensure WSL 2 is installed and enabled. If you haven't used it before, the easiest way is to:

- Open **PowerShell as Administrator**.
    
- Run this command:
    
    PowerShell
    
    ```
    wsl --install
    ```
    
- **Restart** your computer when prompted. This usually installs WSL, the WSL kernel update, and a default Linux distribution (like Ubuntu).
    

##### 2. Download and Install Docker Desktop

1. Go to the official Docker website: [Docker Desktop](https://www.docker.com/products/docker-desktop/).
    
2. Download the **Docker Desktop for Windows** installer (`.exe`).
    
3. Run the downloaded installer and follow the on-screen instructions. It will likely ask you to confirm that WSL 2 integration is enabled (make sure it is).
    
4. You might need to **restart** your computer again after the installation.
    

##### 3. Run Docker Desktop

After restarting, find "Docker Desktop" in your Start Menu and run it. The Docker whale icon 🐳 should appear in your system tray. Docker Desktop manages the Docker engine running inside WSL 2 for you. You can usually run `docker` commands from PowerShell or Command Prompt.

---

#### Linux (Ubuntu) 🐧

On Ubuntu, you install the Docker Engine directly using the command line. These are the same steps as before:

##### 1. Set Up Docker's Repository

Bash

```
# Update package lists and install dependencies
sudo apt update
sudo apt install ca-certificates curl

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package lists again
sudo apt update
```

##### 2. Install Docker Engine

Bash

```
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

##### 3. Add Your User to the `docker` Group (Important!)

This allows you to run `docker` commands without `sudo`.

Bash

```
sudo usermod -aG docker $USER
```

**You MUST log out and log back in** for this change to take effect!

##### 4. Test Installation

Verify it works by running this test command:

Bash

```
docker ps
```

This [guide to installing Docker on Windows 11](https://www.youtube.com/watch?v=mS26N5cLBe8) might be helpful if you prefer a video walkthrough for the Windows steps.

### Installing Dependencies 
On vs code open a new terminal, navigate to the project folder and run these commands.

#### Create a venv

You need to create a venv in the project folder to install the dependencies 

##### For winodos 
create the venv
```bash
virtualenv venv
```

activate the venv
```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

```bash
venv/Scripts/activate
```
##### For Linux
create the venv
```bash
python3 venv -m venv
```

activate the venv
```bash
source venv/bin/activate
```

Your venv should be now activated.

#### Install dependencies 

Run this command to install the project dependencies (make sure your in the project folder)
```bash
pip install -r requirements.txt
```


### Running the project :

#### Launching redis container using docker 
run this command in the terminal
```bash 
docker compose up -d
```
 
#### Launching celery worker 
```bash
celery -A main worker -l info
```

#### Executing the project main.py file
```bash
python main.py
```