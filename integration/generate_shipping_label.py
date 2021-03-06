from zoho.invoicing.generate_rts_file import generate_files
from udaan.orders.upload_rts import upload_and_start_shipping_label_job


def generate(invoice_number):
    output_file = generate_files(invoice_number)
    pdf_path = upload_and_start_shipping_label_job(output_file)
    print("File downloaded at path: file://{}".format(pdf_path))
    return pdf_path


