from integration.udaan import get_auth_token, requests
from integration import home
from time import sleep

headers = {'authorization': 'Bearer {}'.format(get_auth_token())}


def upload_rts_file(file_path):
    print("Uploading File")
    files = {'file': open(file_path, 'rb')}
    r = requests.post('https://udaan.com/api/batch-job/v1/start/BULK_RTS_AND_INVOICE_V2', files=files, headers=headers)
    job_id = r.json()[0]
    return job_id


def start_shipping_label_job(task_id, result_file_id):
    print("Starting Shipping Label Job")
    r = requests.post('https://udaan.com/api/batch-job/v1/start/shipping-label/job/{}?resultId={}&invoiceDetails=true'.format(task_id, result_file_id), headers=headers)
    return str(r.text)


def poll_task(job_id):
    retry = 5
    while retry > 0:
        sleep(1)
        task = fetch_task(job_id)
        retry -= 1
        print("Task status: {}".format(task['taskStatus']))
        if task['taskStatus'] == 'TASK_COMPLETED':
            return task
        print("Retry after 1 seconds")
    return None


def fetch_task(job_id):
    all_tasks = fetch_all_tasks()
    for task in all_tasks['tasks']:
        if task['taskId'] == job_id:
            return task
    raise Exception("Task Not found")


def fetch_all_tasks():
    r = requests.get('https://udaan.com/api/batch-job/v1/all-jobs', headers=headers)
    all_tasks = r.json()
    return all_tasks


def download_storage_file(task_id, storage_id, invoice_id):
    url = 'https://udaan.com/api/batch-job/v1/download/job/{}/{}'.format(task_id, storage_id)
    r = requests.get(url, headers=headers)
    print("Downloading file: {}".format(url))
    file_path = home / '{}-{}.pdf'.format(task_id[:6], invoice_id if invoice_id else 'Unknown')
    with open(file_path, 'wb') as f:
        f.write(r.content)
    return file_path


def download_shipping_label_file(task_id, invoice_id):
    shipping_task = fetch_shipping_label_task(task_id)
    shipping_task = poll_task(shipping_task['taskId'])
    return download_storage_file(shipping_task['taskId'], shipping_task['storageId'], invoice_id)


def fetch_shipping_label_task(task_id):
    all_tasks = fetch_all_tasks()
    for task in all_tasks['tasks']:
        if task_id in task['taskType']:
            return task
    raise Exception("Task Not found")


def upload_and_start_shipping_label_job(file_path, invoice_id=None):
    job_id = upload_rts_file(file_path)
    print("Uploaded file: {}\nJobID: {}".format(file_path, job_id))
    print("Waiting for job to finish")
    task = poll_task(job_id)
    if not task:
        print ("Job timed out")
    else:
        return start_and_download_shipping_label(task['taskId'], task['taskResultProperties']['RESULT_FILE_ID'], invoice_id)
    return None


def start_and_download_shipping_label(taskId, result_file_id, invoice_id):
    status = start_shipping_label_job(taskId, result_file_id)
    print(status)
    if status == 'true':
        return download_shipping_label_file(taskId, invoice_id)
    else:
        print("Starting Shipping Label Job failed.")
    return None
