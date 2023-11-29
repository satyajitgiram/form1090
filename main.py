import json
import config
import requests
from gevent.pywsgi import WSGIServer
from flask import Flask,jsonify,request, send_file, render_template
from flask_cors import CORS, cross_origin
from helpers.g_sheet_handler import GoogleSheetHandler
from datetime import datetime
from pathlib import Path
import pdfkit  # Added for PDF generation
import smtplib  # Added for sending emails
from email.mime.multipart import MIMEMultipart  # Added for email handling
from email.mime.text import MIMEText  # Added for email handling
from email.mime.application import MIMEApplication  # Added for email handling
import email.header
from requests.exceptions import RequestException
import os


date = datetime.now()

app =   Flask(__name__, template_folder='templates', static_url_path='/static')
CORS(app)

def pop_push_func(data_list, index, data):
    data_list.pop(index)
    data_list.insert(index,data)

@app.route('/', methods = ['GET', 'POST'])
@cross_origin(origin='*')
def home():

    if request.method == 'GET':
        phoneCode = request.args.get('CheckPhoneCode')
        passport_no = request.args.get('id')
        action = request.args.get('action')
        phone_no = request.args['Phone']
        try:
            data_ = GoogleSheetHandler(sheet_name=config.SHEET_USER_DATA_GET, spreadsheet_id=config.SAMPLE_SPREADSHEET_ID).getsheet_records()
        except Exception as e:
            return "Internal Server Error-Could Not Get Data from Database", 500

        if passport_no == "" or passport_no is None:
            res = {}
            res["studentStatus"] = False
            res["message"] = "אתה לא נמצא ברשימות או שמספר הטלפון שלך לא מעודכן במערכת נא פנה לאחראי,You are not on the lists or your phone number is not updated in the system, please contact the manager"
            return json.dumps(res)

        checkData = [item for item in data_ if item[11] == str(passport_no)]
        if len(checkData) == 0:
            res = {}
            res["studentStatus"] = False
            res["message"] = "אתה לא נמצא ברשימות או שמספר הטלפון שלך לא מעודכן במערכת נא פנה לאחראי,You are not on the lists or your phone number is not updated in the system, please contact the manager"
            return json.dumps(res)

        if phoneCode is None:
            if len(passport_no) > 0 and len(phone_no) > 0:
                for data in data_[2:]:
                    if action == 'GetStudentsByMosd':
                        if data[11] == passport_no and data[28] == phone_no[1:]:
                            print("--------------------------------------- Matched ------------------------")
                            customValue = str(request.query_string, 'utf-8')
                            customResponse = [[date.strftime("%d/%m/%Y, %H:%M:%S"), 'GET', customValue]]
                            data_ = GoogleSheetHandler(data = customResponse,
                                        sheet_name=config.SHEET_USER_DATA_LOG,
                                        spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()
                            response = requests.get(f'https://www.call2all.co.il/ym/api/RunTzintuk?token=025089532:7974153&callerId=RAND&phones=${phone_no}')
                            response_json = json.loads(response.text)

                            if response_json['responseStatus'] == 'ERROR':
                                data_append = [[date.strftime("%d/%m/%Y %H:%M:%S"),response_json['responseStatus'],int(phone_no),'',response.text]]
                                GoogleSheetHandler(data = data_append, sheet_name=config.SHEET_CODE_STORAGE,
                                            spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()
                                return json.dumps({
                                        "Data" : data,
                                        "Validation" : "Successful",
                                        "studentStatus": True,
                                        "CheckPhoneCodeStatus": False,
                                        "Passport Number" : passport_no,
                                        "Phone Number" : phone_no,
                                        'message' : f'Some Error occured : {response_json["message"]}'
                                        })
                            elif response_json['responseStatus'] == 'Exception':
                                data_append = [[date.strftime("%d/%m/%Y %H:%M:%S"),response_json['responseStatus'],int(phone_no),'',response.text]]
                                GoogleSheetHandler(data = data_append, sheet_name=config.SHEET_CODE_STORAGE,
                                            spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()

                                return json.dumps({
                                        "Data" : data,
                                        "studentStatus" : True,
                                        "CheckPhoneCodeStatus" : False,
                                        "Passport Number" : passport_no,
                                        "Phone Number" : phone_no,
                                        "Validation" : "Successful",
                                        'message' : f'Exception occured : {response_json["message"]}'
                                        })
                            else:
                                data_append = [[date.strftime("%d/%m/%Y %H:%M:%S"),response_json['responseStatus'],int(phone_no),response_json['verifyCode'],response.text]]
                                GoogleSheetHandler(data = data_append, sheet_name=config.SHEET_CODE_STORAGE,
                                                spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()


                            # Define a mapping of indices to keys for the data list
                                keys_mapping = {
                                    9: "FirstName", 10: "Family", 6: "Zihuy", 7: "ZihuyType", 5: "StudyTypeID",
                                    12: "BDE", 14: "Group", 0: "Mosd", 15: "GroupZaraeim", 23: "KolelBoker",
                                    24: "KolelZarim", 38: "Mail", 33: "StreetNum", 32: "Street", 31: "City",
                                    34: "Bank", 35: "Snif", 36: "Account", 39: "MosdName", 40: "MosdAdd",
                                    41: "MosdAuthorizedName", 2: "JoiningDate", 37: "MosdId", 4: "MaritalStatus",
                                    43: "AdminMail", 8: "Country"
                                }

                                # Create studentData dictionary using a dictionary comprehension
                                studentData = {keys_mapping[i]: data[i] if len(data) > i else '' for i in keys_mapping}


                                res = json.dumps({
                                        #"studentData": studentData,
                                        "Passport Number" : passport_no,
                                        "Phone Number" : phone_no,
                                        "Validation" : "Successful",
                                        "studentStatus": True,
                                        "CheckPhoneCodeStatus": True,
                                        "PhoneLast4": f"******{phone_no[-4:]}",
                                        "message" : f"A call was sent to phone ******{phone_no[-4:]}"
                                        })

                                # GoogleSheetHandler(data = [res], sheet_name=config.SHEET_USER_DATA_FSR,spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()

                                return res
                    elif action == 'GetStudentsByMosd':
                        if data[11] == passport_no and (data[45] == phone_no[1:] or data[46] == phone_no[1:]):
                            print("----------------------- Matched for Admin ---------------------")
                            customValue = str(request.query_string, 'utf-8')
                            customResponse = [[date.strftime("%d/%m/%Y, %H:%M:%S"), 'GET', customValue]]
                            data_ = GoogleSheetHandler(data = customResponse,
                                        sheet_name=config.SHEET_USER_DATA_LOG,
                                        spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()
                            response = requests.get(f'https://www.call2all.co.il/ym/api/RunTzintuk?token=025089532:7974153&callerId=RAND&phones=${phone_no}')
                            response_json = json.loads(response.text)

                            if response_json['responseStatus'] == 'ERROR':
                                data_append = [[date.strftime("%d/%m/%Y %H:%M:%S"),response_json['responseStatus'],int(phone_no),'',response.text]]
                                GoogleSheetHandler(data = data_append, sheet_name=config.SHEET_CODE_STORAGE,
                                            spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()
                                return json.dumps({
                                        "Data" : data,
                                        "Validation" : "Successful",
                                        "studentStatus": True,
                                        "CheckPhoneCodeStatus": False,
                                        "Passport Number" : passport_no,
                                        "Phone Number" : phone_no,
                                        'message' : f'Some Error occured : {response_json["message"]}'
                                        })
                            elif response_json['responseStatus'] == 'Exception':
                                data_append = [[date.strftime("%d/%m/%Y %H:%M:%S"),response_json['responseStatus'],int(phone_no),'',response.text]]
                                GoogleSheetHandler(data = data_append, sheet_name=config.SHEET_CODE_STORAGE,
                                            spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()

                                return json.dumps({
                                        "Data" : data,
                                        "studentStatus" : True,
                                        "CheckPhoneCodeStatus" : False,
                                        "Passport Number" : passport_no,
                                        "Phone Number" : phone_no,
                                        "Validation" : "Successful",
                                        'message' : f'Exception occured : {response_json["message"]}'
                                        })
                            else:
                                data_append = [[date.strftime("%d/%m/%Y %H:%M:%S"),response_json['responseStatus'],int(phone_no),response_json['verifyCode'],response.text]]
                                GoogleSheetHandler(data = data_append, sheet_name=config.SHEET_CODE_STORAGE,
                                                spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()


                            # Define a mapping of indices to keys for the data list
                                keys_mapping = {
                                    9: "FirstName", 10: "Family", 6: "Zihuy", 7: "ZihuyType", 5: "StudyTypeID",
                                    12: "BDE", 14: "Group", 0: "Mosd", 15: "GroupZaraeim", 23: "KolelBoker",
                                    24: "KolelZarim", 38: "Mail", 33: "StreetNum", 32: "Street", 31: "City",
                                    34: "Bank", 35: "Snif", 36: "Account", 39: "MosdName", 40: "MosdAdd",
                                    41: "MosdAuthorizedName", 2: "JoiningDate", 37: "MosdId", 4: "MaritalStatus",
                                    43: "AdminMail", 8: "Country"
                                }

                                # Create studentData dictionary using a dictionary comprehension
                                studentData = {keys_mapping[i]: data[i] if len(data) > i else '' for i in keys_mapping}


                                res = json.dumps({
                                        #"studentData": studentData,
                                        "Passport Number" : passport_no,
                                        "Phone Number" : phone_no,
                                        "Validation" : "Successful",
                                        "studentStatus": True,
                                        "CheckPhoneCodeStatus": True,
                                        "PhoneLast4": f"******{phone_no[-4:]}",
                                        "message" : f"A call was sent to phone ******{phone_no[-4:]}"
                                        })

                                # GoogleSheetHandler(data = [res], sheet_name=config.SHEET_USER_DATA_FSR,spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()

                                return res

                customValue = str(request.query_string, 'utf-8')
                customResponse = [[date.strftime("%d/%m/%Y, %H:%M:%S"), 'GET', customValue]]
                data_ = GoogleSheetHandler(data = customResponse,
                                    sheet_name=config.SHEET_USER_DATA_LOG,
                                    spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()
                return json.dumps({
                                "Passport Number" : passport_no,
                                "Phone Number" : phone_no,
                                "studentStatus" : False,
                                "CheckPhoneCodeStatus" : False,
                                "message" : "אתה לא נמצא ברשימות או שמספר הטלפון שלך לא מעודכן במערכת נא פנה לאחראי,You are not on the lists or your phone number is not updated in the system, please contact the manager",
                            })


            else:
                customValue = str(request.query_string, 'utf-8')
                customResponse = [[date.strftime("%d/%m/%Y, %H:%M:%S"), 'GET', customValue]]
                data_ = GoogleSheetHandler(data = customResponse,
                                    sheet_name=config.SHEET_USER_DATA_LOG,
                                    spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()

                return json.dumps(
                    {
                        "Passport Number" : passport_no,
                        "Phone Number" : phone_no,
                        "Validation" : "Failed",
                        "Error Msg":"please fill all the fields",
                    }
                )
        else :
            otp = request.args.get('CheckPhoneCode')
            if len(passport_no) > 0 and len(phone_no) > 0:
                def fetch_otp_from_google_sheet(passport_no, phone_no):
                    try:
                        data_ = GoogleSheetHandler(sheet_name=config.SHEET_CODE_STORAGE, spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).getsheet_records()
                    except Exception as e:
                        return "Internal Server Error - Could not get data from Database", 500

                    for data in data_[1:]:
                        if data[2] == str(phone_no[1:]) and data[1] == "OK":
                            return data[3]  # Replace XX with the column index where OTP is stored in your sheet

                    return None  # No matching OPT found
                
                for data in data_[2:]:

                    if data[11] == passport_no and data[28] == phone_no[1:]:
                        customValue = str(request.query_string, 'utf-8')
                        customResponse = [[date.strftime("%d/%m/%Y, %H:%M:%S"), 'GET', customValue]]
                        data_ = GoogleSheetHandler(data = customResponse,
                                    sheet_name=config.SHEET_USER_DATA_LOG,
                                    spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()
                        #response = requests.get(f'https://www.call2all.co.il/ym/api/RunTzintuk?token=025089532:7974153&callerId=RAND&phones=${phone_no}')
                        #response_json = json.loads(response.text)


                        studentData = {
                            "FirstName": data[9] if len(data) > 9 else "",
                            "Family": data[10] if len(data) > 10 else "",
                            "Zihuy": data[6] if len(data) > 6 else "",
                            "ZihuyType": data[7] if len(data) > 7 else "",
                            "StudyTypeID":  "StudyType_" + data[5],
                            "BDE": data[12] if len(data) > 12 else "",
    				        #"MosdOLD": f"{data[0] if len(data) > 0 else ''}, {data[5] if len(data) > 5 else ''}",
    				        "Group": data[14] if len(data) > 14 else '',
                            "Mosd": data[0] if len(data) > 0 else '',
                            "GroupZaraeim": data[15] if len(data) > 15 else "",
                            "KolelBoker": data[23] if len(data) > 23 else "",
                            "KolelZarim": data[24] if len(data) > 24 else "",
                            "Mail": data[38] if len(data) > 38 else "",
                            "StreetNum": data[33] if len(data) > 33 else "",
                            "Street": data[32] if len(data) > 32 else "",
                            "City": data[31] if len(data) > 31 else "",
                            "Bank": data[34] if len(data) > 34 else "",
                            "Snif": data[35] if len(data) > 35 else "",
                            "Account": data[36] if len(data) > 36 else "",
                            "MosdName": data[39] if len(data) > 39 else "",
                            "MosdAdd": data[40] if len(data) > 40 else "",
                            "MosdAuthorizedName": data[41] if len(data) >= 41 else "",
                            "JoiningDate": data[2] if len(data) >= 2 else "",
                            "MosdId": data[37] if len(data) > 37 else "",
                            "StudyType": data[5] if len(data) > 5 else "",
                            "MaritalStatus": data[4] if len(data) > 4 else "",
                            "AdminMail": data[43] if len(data) > 43 else '',
                            "Country": data[8] if len(data) > 8 else ""
                        }

                        res = {
                                # "Data" : data,
                                "studentData": studentData,
                                "Passport Number" : passport_no,
                                "Phone Number" : phone_no,
                                "Validation" : "Successful",
                                "studentStatus": True,
                                "CheckPhoneCodeStatus": True,
                                "PhoneLast4": f"******{phone_no[-4:]}",
                                "message" : "otp validation successfull"
                                }

                        #GoogleSheetHandler(data = customResponse,
                        #           sheet_name=config.SHEET_USER_DATA_LOG,
                        #           spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()
                        json_string = json.dumps(res)
                        actual_otp = fetch_otp_from_google_sheet(passport_no, phone_no)

                        if actual_otp is None:
                            return json.dumps({"message": "Could not get OTP, please try again later"})

                        return json_string if otp == actual_otp and len(otp) > 0 else json.dumps({"status": 400, "CheckPhoneCodeStatus": False, "studentStatus": True, "message": "OTP validation failed"})

                    else:
                        pass


    if request.method == 'POST':

        customValue = dict(request.form)
        requestData = json.dumps( request.form)
        requestData = json.loads(requestData)
        json_str = list(requestData.keys())[0]
        formData = json.loads(json_str)
        ishur1_value = formData.get('Ishur1Price12')
        customResponse = [[date.strftime("%d/%m/%Y, %H:%M:%S"), 'POST',
                            str(customValue)]]

        GoogleSheetHandler(data = customResponse, sheet_name=config.SHEET_USER_DATA_FSP, spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()

        data_list = ["-"] * 86  # Initialize data_list with 86 "-"

        # Define a list of keys to extract from formData
        keys_to_extract = [
            'Ishur1', 'Ishur2', 'Ishur3', 'Ishur4', 'Ishur5', 'Ishur6', 'Ishur7', 'Ishur8', 'Ishur9', 'Ishur10', 'Zava', 'FirstName', 'Family', 'Tel1', 'Zihuy', 'Zeout', 'Darkon', 'SendMailFax', 'Mail', 'Fax',
            'remarks', 'Ishur1Shana', 'Ishur1Price10', 'Ishur1Price11', 'Ishur1Price12', 'Ishur1none', 'Ishur4Price', 'Ishur4none', 'ZavaNameAv', 'BDE', 'ZavaEnlistmentDate', 'ZavaEnlistmentDatenon', 'ZavaLastEnlistmentDate',
            'ZavaLastEnlistmentDatenon', 'ZavaRemoveStatus', 'ZavaStatus', 'City', 'Street', 'StreetNum', 'ZavaShipping', 'Ishur11ShippingCtovet', 'Ishur11ShippingCtovetCity', 'Ishur11ShippingCtovetStreet', 'Ishur11ShippingCtovetStreetNum',
            'Ishur11ShippingTaDoar', 'Ishur7Siba', 'Boker', 'Zaraeim', 'Mosd',  'Ishur7Siba', 'VisaFromDate', 'VisaToDate','LastYear', 'Date', 'TopesId','Ishur8AmIsIsral', 'Ishur8DarkonAm', 'IshurMotherContry', 'Ishur8NameAm', 'Ishur8NumKids', 'DivOpenIshur8Kids_1Name', 'DivOpenIshur8Kids_1Darkon', 'DivOpenIshur8Kids_1country',
            'DivOpenIshur8Kids_2Name', 'DivOpenIshur8Kids_2Darkon', 'DivOpenIshur8Kids_2country', 'DivOpenIshur8Kids_3Name', 'DivOpenIshur8Kids_3Darkon', 'DivOpenIshur8Kids_3country', 'DivOpenIshur8Kids_4Name', 'DivOpenIshur8Kids_4Darkon',
            'DivOpenIshur8Kids_4country', 'DivOpenIshur8Kids_5Name', 'DivOpenIshur8Kids_5Darkon', 'DivOpenIshur8Kids_5country', 'DivOpenIshur8Kids_6Name', 'DivOpenIshur8Kids_6Darkon', 'DivOpenIshur8Kids_6country', 'DivOpenIshur8Kids_7Name',
            'DivOpenIshur8Kids_7Darkon', 'DivOpenIshur8Kids_7country', 'DivOpenIshur8Kids_8Name', 'DivOpenIshur8Kids_8Darkon', 'DivOpenIshur8Kids_8country'
        ]

        # Loop through keys_to_extract and populate data_list
        for i, key in enumerate(keys_to_extract, start=4):
            if i < len(data_list):
                data_list[i] = formData.get(key, "-")

            else:
                # Handle the case where the index is out of range
                pass

        data_list[1] = date.strftime("%d/%m/%Y %H:%M:%S")
        data_list[82] = "SignData"
        data_list[83] = "response"
        data_list[84] = formData.get('FatherName') or "-"
        data_list[85] = formData.get('PassportExpiration') or "-"


        # -------------------- send mail -----------------------
        try:       
            # Sending emails
            TofesId_value = formData.get('TofesId', "")

            # Check for available email or fax
            if not formData.get('Mail') and not formData.get('Fax', ""):
                print("MAIL OR FAX not available to send mail")
            else:
                formatted_date = datetime.now().strftime("%d-%m-%Y")
                formatted_month_year = datetime.now().strftime("%m-%Y")
                data = formData
                data['generated_report_report_date'] = formatted_date
                data['generated_report_month_year'] = formatted_month_year

                if data_list[19] is None or data_list[19] == "":
                    data["student_identity"] = data_list[19]
                else:
                    data["student_identity"] = data_list[20]

                # Check for available Ishur keys and generate template names accordingly
                for i in range(1, 21):
                    ishur_key = f'Ishur{i}'

                    if ishur_key in formData:
                        # Remove ",600" from the Mosd value
                        mosd_value = formData.get('Mosd', "").replace(",600", "")

                        template_name = f"{ishur_key}.html"
                        template_path = Path("/var/www/html/puc-api_v2/templates") / template_name
                        ishur_value = ' '.join(str(data[ishur_key]).split()[1:])
                        subject = f"{formData.get('FirstName', '')} {formData.get('Family', '')} {formData.get('Zeout', '')} {formData.get('Darkon', '')} {data['student_identity']} {ishur_value}"
                        filename = f"{ishur_key} {data['student_identity']} {mosd_value}"

                        if template_path.is_file():
                            makePDF(data, email=formData.get('Mail', ""), fax=formData.get("Fax", ""), template=template_name, mosd_value=mosd_value, subject=subject, filename=filename)
                        else:
                            print(f"Template '{template_name}' does not exist. Email not sent.")


        except Exception as e:
            print("Error while getting data from form - ", e)
            pass        
	# ------------------------- send mail end ------------------- 

        
        #GoogleSheetHandler(data = [data_list], sheet_name=config.SHEET_FORM_DATA_STORAGE,spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()

        customResponse = [[date.strftime("%d/%m/%Y, %H:%M:%S"), 'DATA: '+  str(data_list), 'Status: Success']]
        res = {
                "Update" : "Success",
                "Request Value" : customValue,
                "Update Data" : data_list,
            }
        GoogleSheetHandler(data = customResponse, sheet_name=config.SHEET_USER_DATA_FSR,spreadsheet_id=config.SAMPLE_SPREADSHEET_ID_FSP).appendsheet_records()
        return res


def sendMail(email=None, pdf=None, name=None, subject=None, filename=None):
    if email is None or pdf is None:
        return False
    
    try:
        sender_email = '6708410@GMAIL.COM'
        sender_password = 'fwivtwjvkrxaajnl'
        receiver_email = email
        subject = subject or 'Your Form Submission'
        message = 'Please find attached your PDF file.שלום רב מצוב הטופס שהזמנת'

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)

            # Create the email message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))

            # Attach the PDF
            pdf_attachment = MIMEApplication(pdf, _subtype='pdf')
            pdf_attachment.add_header('Content-Disposition', f'attachment; filename={filename}.pdf')
            msg.attach(pdf_attachment)

            # Send the email
            server.sendmail(sender_email, receiver_email, msg.as_string())

        print(f"------------ Email Sent successfully. PDF generated sent to email - {receiver_email}-------------")
        return True
    except Exception as e:
        print("Exception while sending an email ->", e)
        return False


def makePDF(data=None, email=None, fax=None, template=None, mosd_value=None, subject=None, filename=None):
    if data is None or email is None or template is None or mosd_value is None or subject is None:
        return False

    try:
        # name = data["student_first_name"] + "_" + data['student_last_name']
        html_content = render_template(template, data=data, url="https://mllcr.info/static/images", mosd_value=mosd_value)

        # Define PDF options
        pdf_options = {'page-size': 'A4', 'orientation': 'Portrait', "enable-local-file-access": ""}

        # Reuse the length check result
        is_valid_email = len(email) > 5

        if is_valid_email:
            pdf = pdfkit.from_string(html_content, False, options=pdf_options)
            name = template[:-5]
            sendMail(email, pdf, name=name, subject=subject, filename=filename)

        elif len(fax) > 7:
            file_path = os.path.join("/root/puc-api_v2/FaxPDF", f"{filename}.pdf")
            fax_pdf = pdfkit.from_string(html_content, False, options=pdf_options)

            with open(file_path, 'wb') as pdfFile:
                pdfFile.write(fax_pdf)
                print("PDF GENERATED FOR FAX SEND")

            send_fax(fax_number=fax, file_path=file_path)
            os.remove(file_path)
            print("FILE REMOVED WHICH IS SENT IN FAX", file_path)

    except Exception as e:
        print("+++++++++++++++++++ Exception while sending mail - ", e)


def send_fax(fax_number: str, file_path: str):
    url = "https://www.myfax.co.il/action/faxUpload.do"
    data = {
        "email": config.MYFAX_EMAIL,
        "password": config.MYFAX_PASSWORD,
        "faxNumber": fax_number,
        "resultType": "XML",
    }
    files = {
        'theFile': (file_path, open(file_path, 'rb'), 'application/pdf')
    }

    try:
        response = requests.post(url, data=data, files=files)

        if response.status_code == 200:
            print("Fax Sent Successfully on fax no", fax_number)
            print(response.json())
        else:
            print(f"Error while sending the fax to fax no {fax_number} -> {response.status_code}:")
            print(response.json())

    except RequestException as e:
        print(f"RequestException while sending the fax to fax no {fax_number}:", str(e))

        
       
if __name__=='__main__':
    #app.run(host='0.0.0.0', port=9000, debug=True)
    app.run(ssl_context=('cert.pem','key.pem'))
    # http_server = WSGIServer(('74.208.188.36', 5000), app)
    http_server.serve_forever()
