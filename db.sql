    CREATE TABLE purchase_orders(
        po_number VARCHAR(50) NOT NULL PRIMARY KEY,
        vendor_name VARCHAR(50) NOT NULL,
        po_status VARCHAR(50) DEFAULT 'Pending' NOT NULL,
        doc_date DATE NOT NULL,
        due_date VARCHAR(50),
        subtotal DECIMAL(10, 2),
        tax DECIMAL(10, 2),
        Shipping DECIMAL(10, 2)
    );

    CREATE TABLE line_items(
        item_id INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
        item_name VARCHAR(50) NOT NULL,
        quantity VARCHAR(50),
        rate DECIMAL(10, 2),
        amount DECIMAL(10, 2) NOT NULL
    );

    CREATE TABLE invoices(
        invoice_number VARCHAR(50) NOT NULL PRIMARY KEY,
        vendor_name VARCHAR(50) NOT NULL,
        total_amount DECIMAL(10, 2) NOT NULL,
        invoice_date DATE NOT NULL,
        invoice_status VARCHAR(50) DEFAULT 'Pending' NOT NULL,
        due_date VARCHAR(50),
        po_number VARCHAR(50),
        subtotal DECIMAL(10, 2),
        tax DECIMAL(10, 2)
    );
