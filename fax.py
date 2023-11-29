import requests

def send_fax(email: str, password: str, fax_number: str, file_path: str):
    url = "https://www.myfax.co.il/action/faxUpload.do"
    data = {
        "email": email,
        "password": password,
        "faxNumber": fax_number,
        "resultType": "XML",  
    }
    files = {
        'theFile': (file_path, open(file_path, 'rb'), 'application/pdf')
    }
    response = requests.post(url, data=data, files=files)

    if response.status_code == 200:
        print("Request was successful.")
        print(response.text)  
    else:
        print(f"Request failed with status code {response.status_code}:")
        print(response.text)  

# Example usage:
send_fax("6708410@gmail.com", "TXkaTBk84hAt", "077-4702961", "FaxPDF//Ishur3 201110400 580273662.pdf")
