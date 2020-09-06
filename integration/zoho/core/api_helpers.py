from integration.zoho import *
from books.model.Bill import Bill
from books.model.Expense import Expense
from books.model.Invoice import Invoice
from books.model.CustomerPayment import CustomerPayment
from books.model.CreditNoteRefund import CreditNoteRefund
from books.model.VendorPayment import VendorPayment
from books.model.Transaction import Transaction
from books.model.LineItem import LineItem
from time import sleep

invoice_api = zoho_books.get_invoices_api()
expense_api = zoho_books.get_expenses_api()
contact_api = zoho_books.get_contacts_api()
payments_api = zoho_books.get_customer_payments_api()
vendor_payments_api = zoho_books.get_vendor_payments_api()
transaction_api = zoho_books.get_bank_transactions_api()
bills_api = zoho_books.get_bills_api()


def find_invoice_by_number_date(invoice_number, date=None):
    invoices = invoice_api.get_invoices({'invoice_number': invoice_number}).get_invoices()
    for invoice in invoices:
        if not date or invoice.date == date:
            return invoice
    return None


def mark_invoice_as_void(invoice_number=None, invoice_id=None, date=None):
    if not invoice_id:
        invoice = find_invoice_by_number_date(invoice_number, date)
        if not invoice:
            return False
        invoice_id = invoice.invoice_id
    try:
        invoice_api.void_an_invoice(invoice_id)
    except BooksException as e:
        print("Could not void the invoice: {}. Warning: {}".format(invoice_id, e.message))
        return False
    return True


def create_expense(settlement):
    settlement.Description = "{} -- {}".format(settlement.Description, settlement.PaymentReferenceId)
    expense = create_expense_object(settlement)
    expense_api.create(expense)


def create_expense_object(settlement):
    expense = Expense()
    expense.account_id = UDAAN_ADVERTISING_AND_MARKETING_ACCOUNT_ID
    expense.paid_through_account_id = HIVELOOP_LOGISTICS_PAYMENT_ACCOUNT
    expense.date = settlement.Payment_Date.strftime('%Y-%m-%d')
    expense.amount = abs(settlement.Adjusted_Value)
    expense.tax_id = IGST_18_TAX_ID
    expense.is_inclusive_tax = True
    expense.vendor_id = udaan_vendor['vendor_id']
    expense.reference_number = settlement.Invoice_Id
    expense.description = settlement.Description
    expense.product_type = 'service'
    expense.hsn_or_sac = SAC_SALES_MARKETING
    expense.gst_no = udaan_vendor['gst_no']
    expense.gst_treatment = udaan_vendor['gst_treatment']
    expense.destination_of_supply = 'DL'
    return expense


def find_expense(reference_number, date):
    expenses = expense_api.get_expenses({'reference_number': reference_number})
    for expense in expenses.get_expenses():
        if expense.date == date:
            return expense
    return None


def update_expense(expense_id, settlement):
    existing_expense = expense_api.get(expense_id)
    settlement.Adjusted_Value = abs(settlement.Adjusted_Value) + existing_expense.amount
    settlement.Description = "{} -- {}".format(existing_expense.description, settlement.PaymentReferenceId)
    expense = create_expense_object(settlement)
    expense_api.update(expense_id, expense)


def create_payment(customer_id, amount, reference_number, date, description, invoice_id=None,
                   account_id=HIVELOOP_LOGISTICS_PAYMENT_ACCOUNT,
                   invoice_number=None,
                   invoice_date=None, invoice_amount=None):
    payment = create_payment_object(account_id, amount, customer_id, date, description, invoice_date, invoice_id,
                                    invoice_number, reference_number, invoice_amount=invoice_amount)
    return payments_api.create(payment)


def create_payment_object(account_id, amount, customer_id, date, description, invoice_date, invoice_id, invoice_number,
                          reference_number, invoice_amount=None):
    if not invoice_amount:
        invoice_amount = amount
    amount_applied = amount if amount <= invoice_amount else invoice_amount
    payment = CustomerPayment()
    payment.customer_id = customer_id
    payment.payment_mode = 'cash'
    payment.description = description
    payment.date = date
    payment.reference_number = reference_number
    payment.amount = amount
    payment.account_id = account_id
    if invoice_id:
        payment.invoice_id = invoice_id
        payment_invoice = Invoice()
        payment_invoice.set_invoice_id(invoice_id)
        payment_invoice.set_amount_applied(amount_applied)
        payment_invoice.set_invoice_number(invoice_number)
        payment.invoices = [payment_invoice]
    payment.amount_applied = amount_applied
    return payment


def payment_already_exists(customer_id, amount, reference_number, date):
    payments = payments_api.get_customer_payments(parameter={'reference_number': reference_number})
    for payment in payments.get_customer_payments():
        if payment.customer_id == customer_id and payment.amount == amount and payment.date == date:
            return True
    return False


def find_payment(invoice_id):
    invoice_payments = invoice_api.list_invoice_payments(invoice_id).get_payments()
    if invoice_payments:
        return payments_api.get(invoice_payments[0].payment_id)
    else:
        return None


def refund_amount(customer_payment, date, reference_number, amount, description):
    payments_api.delete(customer_payment.payment_id)
    customer_payment = create_payment(customer_id=customer_payment.customer_id,
                                       amount=customer_payment.amount,
                                       reference_number=customer_payment.reference_number,
                                       date=customer_payment.date,
                                       description=customer_payment.description)
    refund = CreditNoteRefund()
    refund.set_from_account_id(customer_payment.account_id)
    refund.set_date(date)
    refund.set_amount(amount)
    refund.set_reference_number(reference_number)
    refund.set_description(description)
    payments_api.refund(customer_payment.payment_id, refund)



def refund_already_exists(payment, reference_number):
    return reference_number in payment.reference_number


def transfer_fund_exists(account_id, reference_no):
    transactions = transaction_api.get_bank_transactions({'account_id': account_id, 'reference_number': reference_no, 'transaction_type': 'transfer_fund'}).transactions
    return len(transactions) > 0


def transfer_fund(from_account, to_account, amount, date, reference_no, description):
    transaction = Transaction()
    transaction.amount = amount
    transaction.date = date.strftime('%Y-%m-%d')
    transaction.reference_number = reference_no
    transaction.description = description
    transaction.from_account_id = from_account
    transaction.to_account_id = to_account
    transaction.transaction_type = 'transfer_fund'
    transaction_api.create(transaction)


def search_invoice_by_order_id(order_id):
    invoices = invoice_api.get_invoices({'cf_udaan_order_id': order_id}).get_invoices()
    if len(invoices) > 1:
        raise Exception("More than one invoice found for order ID {} found.".format(order_id))
    if len(invoices) == 0:
        return None
    else:
        return invoices[0]


def match_precise_transactions(account_id):
    transactions = transaction_api.get_bank_transactions({'account_id': account_id, 'status': 'uncategorized'}).transactions
    for transaction in transactions:
        if transaction.debit_or_credit == 'debit':
            print(transaction.to_json())
            print("Searching for matching")
            matching = transaction_api.get_matching_transactions(transaction.transaction_id,
                                                                 {'date_after': transaction.date,
                                                                  'date_before': transaction.date,
                                                                  'amount_start': transaction.amount,
                                                                  'amount_end': transaction.amount})
            if matching.transactions:
                matching_trans = matching.transactions[0]
                if matching_trans.offset_account_name == 'Hiveloop Logistics Udaan' and matching_trans.is_best_match:
                    print("found: ")
                    print(matching_trans.to_json())
                    transaction_api.match_a_transaction(transaction.transaction_id, [matching_trans])
                    sleep(3)


def download_all_invoices():
    page = 1
    has_more_page = True
    all_invoices = []
    while has_more_page:
        invoices = invoice_api.get_invoices({'page': page})
        has_more_page = invoices.get_page_context().has_more_page
        all_invoices.extend(invoices.get_invoices())
        page += 1
    return all_invoices


def download_all_contacts():
    page = 1
    has_more_page = True
    all_contacts = []
    while has_more_page:
        contacts = contact_api.get_contacts({'page': page})
        has_more_page = contacts.get_page_context().has_more_page
        all_contacts.extend(contacts.get_contacts())
        page += 1
        break
    return all_contacts


def create_bill(bill_number, vendor_id, bill_date, line_items, notes='', is_inclusive_tax=False):
    bill = Bill()
    bill.set_bill_number(bill_number)
    bill.set_vendor_id(vendor_id)
    bill.set_date(bill_date.strftime('%Y-%m-%d'))
    bill.set_notes(notes)
    bill.set_is_inclusive_tax(is_inclusive_tax)
    for line_item in line_items:
        bill.set_line_items(line_item)
    return bill


def create_line_item(item_id, rate, quantity, discount, tax_id=None):
    line_item = LineItem()
    line_item.set_item_id(item_id)
    line_item.set_rate(rate)
    line_item.set_quantity(quantity)
    line_item.set_discount(None)
    if discount:
        line_item.set_discount(discount)
    if tax_id:
        line_item.set_tax_id(tax_id)
    return line_item


def save_bill(bill):
    bills_api.create(bill)


def create_vendor_payment_object(paid_through_account_id, amount, vendor_id, date, description, bill_id, reference_number, balance):
    payment = VendorPayment()
    payment.vendor_id = vendor_id
    payment.payment_mode = 'cash'
    payment.description = description
    payment.date = date
    payment.reference_number = reference_number
    payment.amount = amount
    payment.paid_through_account_id = paid_through_account_id
    payment.bills = []
    if bill_id:
        bill = Bill()
        bill.bill_id = bill_id
        bill.amount_applied = min(amount, balance)
        payment.bills.append(bill)
    return payment


def save_vendor_payment(vendor_payment):
    vendor_payments_api.create(vendor_payment)


def get_vendor_payment_description(settlement):
    return f'{settlement.Description}--{settlement.Order_Id}--{settlement.PaymentReferenceId}'


def find_vendor_payment(bill_no, vendor_id, date, description):
    payments = vendor_payments_api.get_vendor_payments(parameter={'vendor_id': vendor_id, 'date': date}).get_vendor_payments()
    for payment in payments:
        if payment.description == description:
            payment = vendor_payments_api.get(payment.payment_id)
            for bill in payment.bills:
                if bill.bill_number == bill_no:
                    return payment


def find_bill(vendor_id, bill_no, date):
    bills = bills_api.get_bills(parameter={'vendor_id': vendor_id, 'bill_number': bill_no, 'date': date}).get_bills()
    if bills:
        return bills[0]
    else:
        return None
