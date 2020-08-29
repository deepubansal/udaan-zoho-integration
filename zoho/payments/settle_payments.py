from zoho.payments.invoice_payments_excel_generator import read_settlements, read_rto_sheet, read_payments_sheet,\
    read_reversal_sheet, read_platform_charges_sheet, read_advertisement_charges_sheet, read_logistics_charges_sheet, read_other_charges, read_approved_refund_sheet
from zoho.core.api_helpers import *


def settle_negative_adjustment(settlement):
    refund_order_invoice = is_rvp_refund(settlement)
    if refund_order_invoice:
        pass
    else:
        settle_expense(settlement)


def settle_refund(refund):
    invoice = find_invoice_by_number_date(refund.For_Invoice_Id)
    if invoice:
        invoice_id = invoice.invoice_id
        payment = find_payment(invoice_id)
        if not payment:
            print("Payment not found. So can not refund.")
        else:
            refund_amount(payment, refund.Refund_Date.strftime('%Y-%m-%d'), refund.Return_Id,
                          refund.Refund_Amount, '{}-{}'.format(refund.For_Invoice_Id, refund.Description))
        mark_invoice_as_void(invoice_id=invoice_id)
    else:
        print("Invoice not found. Remove any RTO Claim if already created.")


def settle_approved_refunds(refunds):
    for refund in refunds:
        print("Picking Approved Refund: {}".format(refund))
        settle_refund(refund)


def is_rvp_refund(settlement):
    import re
    matched = re.match('(Approved refund for Order Id )([A-Z0-9]{14}) (\(invoice ref: )([^\s]+)\)',
                       settlement.Description)
    if matched:
        groups = matched.groups()
        return (groups[1], groups[3])
    else:
        return None


def read_order_id_from_description(description):
    import re
    matched = re.match('(Partial/Full Refund for )(OD[A-Z0-9]{12})', description)
    if matched:
        groups = matched.groups()
        return groups[1]
    else:
        matched = re.match('Reversing incorrect RTO status for (RET\d*) and order Id (OD[A-Z0-9]{12})', description)
        if matched:
            groups = matched.groups()
            return groups[1]
        else:
            return None


def settle_rto_payment(settlement):
    mark_invoice_as_void(invoice_number=settlement.Invoice_Id)
    record_rto_payment(settlement)


def record_rto_payment(settlement):
    reference_number = 'RTO-Claim-{}-{}'.format(settlement.Invoice_Id, settlement.PaymentReferenceId)
    settlement_date = settlement.Payment_Date.strftime('%Y-%m-%d')
    if payment_already_exists(RTO_CLAIM_DUMMY_CUSTOMER_ID, settlement.Adjusted_Value, reference_number,
                              settlement_date):
        print("Payment for RTO already imported in zoho. Skipping Settlement: {}".format(settlement))
    else:
        create_payment(RTO_CLAIM_DUMMY_CUSTOMER_ID, settlement.Adjusted_Value, reference_number,
                       settlement_date, settlement.Description)


def settle_rto_reversal_payment(reversal):
    order_id = read_order_id_from_description(reversal.Description)
    if order_id:
        invoice_id = search_invoice_by_order_id(order_id).invoice_number
    else:
        invoice_id = 'non-rto-reversal'
    reference_number = 'RTO-Claim-{}-{}'.format(invoice_id, reversal.PaymentReferenceId)
    settlement_date = reversal.Payment_Date.strftime('%Y-%m-%d')
    if payment_already_exists(RTO_CLAIM_DUMMY_CUSTOMER_ID, reversal.Adjusted_Value, reference_number,
                              settlement_date):
        print("Payment for RTO already imported in zoho. Skipping reversal: {}".format(reversal))
    else:
        create_payment(RTO_CLAIM_DUMMY_CUSTOMER_ID, reversal.Adjusted_Value, reference_number,
                       settlement_date, reversal.Description)


def settle_expense(settlement):
    bill = find_bill(vendor_id=HIVELOOP_LOGISTICS_VENDOR_ID, bill_no=settlement.Invoice_Id, date=settlement.Invoice_Date.strftime('%Y-%m-%d'))
    if not bill:
        raise Exception("Bill No. {} not found. This should not happen".format(settlement.Invoice_Id))
    payment = find_vendor_payment(settlement.Invoice_Id, HIVELOOP_LOGISTICS_VENDOR_ID, settlement.Payment_Date.strftime('%Y-%m-%d'), get_vendor_payment_description(settlement))
    if payment:
        print("Payment already created in zoho. Skipping Settlement: {}".format(settlement))
        return
    vendor_payment = create_vendor_payment_object(HIVELOOP_LOGISTICS_PAYMENT_ACCOUNT, abs(settlement.Adjusted_Value),
                                                  HIVELOOP_LOGISTICS_VENDOR_ID,
                                                  settlement.Payment_Date.strftime('%Y-%m-%d'), get_vendor_payment_description(settlement),
                                                  bill.bill_id,
                                                  reference_number=settlement.PaymentReferenceId, balance=bill.balance)
    save_vendor_payment(vendor_payment)


def settle_customer_payment(settlement):
    invoice_date = settlement.Invoice_Date.strftime('%Y-%m-%d')
    invoice = find_invoice_by_number_date(settlement.Invoice_Id)
    date = settlement.Payment_Date.strftime('%Y-%m-%d')
    payment_reference_id = '{}-{}'.format(settlement.Invoice_Id, settlement.PaymentReferenceId)
    if not invoice:
        # product is either lost or is in RTO
        record_rto_payment(settlement)
    elif invoice.status != 'void':
        if payment_already_exists(invoice.customer_id, settlement.Adjusted_Value, payment_reference_id, date):
            print("Customer Payment already imported in zoho. Skipping Settlement: {}".format(settlement))
        else:
            create_payment(invoice.customer_id,
                           settlement.Adjusted_Value,
                           payment_reference_id,
                           date,
                           settlement.Description, invoice_id=invoice.invoice_id,
                           invoice_number=settlement.Invoice_Id,
                           invoice_date=invoice_date,
                           invoice_amount=invoice.total)


def void_rto_invoices(rtos):
    for rto in rtos:
        print("Picking RTO row: {}".format(rto))
        mark_invoice_as_void(invoice_number=rto.Invoice_Id)


def import_bank_transfers(transfers):
    for bank_transfer in transfers:
        target_account = ICICI_ACCOUNT_ID
        print("Picking Bank Transfer row: {}".format(target_account))
        if transfer_fund_exists(HIVELOOP_LOGISTICS_PAYMENT_ACCOUNT, bank_transfer.UTR):
            print(f"Transfer fund already exists for reference no: {bank_transfer.UTR}")
        else:
            transfer_fund(HIVELOOP_LOGISTICS_PAYMENT_ACCOUNT,
                          target_account,
                          bank_transfer.Amount,
                          bank_transfer.Payment_Date,
                          bank_transfer.UTR,
                          bank_transfer.UTR)


def create_bill_for_charge(charge, item_id):
    bill = find_bill(vendor_id=HIVELOOP_LOGISTICS_VENDOR_ID, bill_no=charge.Invoice_Number, date=charge.Invoice_Date.strftime('%Y-%m-%d'))
    if not bill:
        item = create_line_item(item_id, charge.Invoice_Amount, 1, 0, IGST_18_TAX_ID)
        bill = create_bill(charge.Invoice_Number, vendor_id=HIVELOOP_LOGISTICS_VENDOR_ID, bill_date=charge.Invoice_Date,
                           line_items=[item], notes=charge.Invoice_Download_Link, is_inclusive_tax=True)
        save_bill(bill)
    else:
        print("Bill for charge already exists. SKipping Charge: {}".format(charge))


def process_advertisement_charges(advertisements):
    for ad in advertisements:
        create_bill_for_charge(ad, ADVERTISEMENT_CHARGES_ITEM_ID)


def process_logistic_charges(logistics_charges):
    for logistic_charge in logistics_charges:
        create_bill_for_charge(logistic_charge, LOGISTICS_CHARGES_ITEM_ID)


def process_platform_charges(platform_charges):
    for charge in platform_charges:
        create_bill_for_charge(charge, ADVERTISEMENT_CHARGES_ITEM_ID)


def settle_file(file_path):
    settlements = read_settlements(file_path)
    rtos = read_rto_sheet(file_path)
    transfers = read_payments_sheet(file_path)
    reversals = read_reversal_sheet(file_path)
    approved_refunds = read_approved_refund_sheet(file_path)
    platform_charges = read_platform_charges_sheet(file_path)
    logistics = read_logistics_charges_sheet(file_path)
    advertisements = read_advertisement_charges_sheet(file_path)
    other_charges = read_other_charges(file_path)
    process_advertisement_charges(advertisements)
    process_logistic_charges(logistics)
    process_logistic_charges(other_charges)
    process_platform_charges(platform_charges)
    void_rto_invoices(rtos)
    process_settlements(settlements)
    settle_approved_refunds(approved_refunds)
    process_reversals(reversals)
    import_bank_transfers(transfers)


def process_settlements(settlements):
    for settlement in settlements:
        print("Picking settlement row: {}".format(settlement))
        if settlement.Adjusted_Value < 0:
            settle_negative_adjustment(settlement)
        elif settlement.Description.startswith('Partial/Full Refund for '):
            settle_rto_payment(settlement)
        else:
            settle_customer_payment(settlement)


def process_reversals(reversals):
    for reversal in reversals:
        print("Picking reversal row: {}".format(reversal))
        settle_rto_reversal_payment(reversal)
