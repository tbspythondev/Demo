import os
from django.utils.datetime_safe import datetime
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

# model imports
from accounts.models import Profile, LoginInformation

# other imports
import httpagentparser
import requests
from base64 import urlsafe_b64decode, urlsafe_b64encode

from general.models import Subscription

def parse_parts(service, parts, folder_name, message):
    """
    Utility function that parses the content of an email partition
    """
    if parts:
        for part in parts:
            filename = part.get("filename")
            mimeType = part.get("mimeType")
            body = part.get("body")
            data = body.get("data")
            file_size = body.get("size")
            part_headers = part.get("headers")
            if part.get("parts"):
                # recursively call this function when we see that a part
                # has parts inside
                parse_parts(service, part.get("parts"), folder_name, message)
            if mimeType == "text/plain":
                # if the email part is text plain
                if data:
                    text = urlsafe_b64decode(data).decode()
                    print(text)
            elif mimeType == "text/html":
                # if the email part is an HTML content
                # save the HTML file and optionally open it in the browser
                if not filename:
                    filename = "index.html"
                filepath = os.path.join(folder_name, filename)
                print("Saving HTML to", filepath)
                with open(filepath, "wb") as f:
                    f.write(urlsafe_b64decode(data))
            else:
                # attachment other than a plain text or HTML
                for part_header in part_headers:
                    part_header_name = part_header.get("name")
                    part_header_value = part_header.get("value")
                    if part_header_name == "Content-Disposition":
                        if "attachment" in part_header_value:
                            # we get the attachment ID 
                            # and make another request to get the attachment itself
                            print("Saving the file:", filename, "size:", get_size_format(file_size))
                            attachment_id = body.get("attachmentId")
                            attachment = service.users().messages() \
                                        .attachments().get(id=attachment_id, userId='me', messageId=message['id']).execute()
                            data = attachment.get("data")
                            filepath = os.path.join(folder_name, filename)
                            if data:
                                with open(filepath, "wb") as f:
                                    f.write(urlsafe_b64decode(data))

def isMatchDP(text, pattern):
        memo = {}
        def dpToDown(i,j):
            if (i, j)  not in memo:
                if j ==len(pattern):
                    answer=(i == len(text))
                else:
                    firstMatch = (i < len(text) and pattern[j] in {text[i],'.'})

                    if j+1 < len(pattern and pattern[j+1] == '*'):
                        answer = dpToDown(i,j+2) or firstMatch and dpToDown(i+1, j)
                    else:
                        answer = firstMatch and dpToDown (i+1,j+1)
                memo[i,j] = answer
            return memo[i,j]
        return dpToDown(0,0)

def returnNotMatches(a, b):
    return [[x for x in a if x not in b], [x for x in b if x not in a]]

def sendmail(user_id, data):
    try:
        link = "http://localhost:8000/accounts/change_password/" + str(user_id) +"/"
        message_text = "Demo_CRM Platform : Successfull Registration \n\nYou have been successfully added as a user, Please find your credentials below \n\n" + "Email :  " + data['email'] + "\nPassword : " + data['password'] + "\n\nYou can change your password click link below.\n\n" + link
        send_mail('Demo_CRM Platform',message_text,settings.EMAIL_HOST_USER,[data['email']],fail_silently=False)
        return True
    except Exception as e:
        return e

def visitor_ip_address(META):

    x_forwarded_for = META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = META.get('REMOTE_ADDR')
    return ip

def deviceDetails(request, email):
    try:
        META = request.META
        print("META", META)

        # ip = visitor_ip_address(META) # extract ip from META
        data = META["HTTP_USER_AGENT"]   
        user_agent = httpagentparser.simple_detect(data)

        obj =  LoginInformation(email = email, ip_address = META["REMOTE_ADDR"],
                                latitude = META["location"]["latitude"],
                                longitude = META["location"]["longitude"],
                                country = META["location"]["country"],
                                city = META["location"]["city"],
                                browser_name = user_agent[1], os = user_agent[0],
                                login_date = timezone.now(),
                                device_name = "Desktop")
        obj.save()
        return "success"
    except Exception as e:
        return str(e)
		
def check_date(date_time: str):
	c = date_time.replace("-", '').replace(":", "").replace(" ", '')
	if not c.isdigit():
		return None
	b = date_time.split(' ')
	if b.__len__() != 2:
		return None
	date_list = b[0].split('-')
	time_list = b[1].split(':')
	if date_list.__len__() != 3 or time_list.__len__() != 3:
		return None
	date_list = [int(x) for x in date_list]
	time_list = [int(x) for x in time_list]
	date_time = datetime(year=date_list[2], month=date_list[1], day=date_list[0], hour=time_list[0],
						 minute=time_list[1], second=time_list[0])
	return date_time


def create_default_profiles():
	profiles = ['standard', 'administrator']
	if not Profile.objects.filter(name__in=profiles).exists():
		Profile.objects.create(name='standard', description='Standard Profile')
		Profile.objects.create(name='administrator', description='Administrator Profile')


def create_txt_ref():
	from datetime import datetime
	import secrets
	ref = hex(int(datetime.now().timestamp()) + secrets.randbits(255))
	return ref if not Subscription.objects.filter(transaction_ref=ref).exists() else create_txt_ref()



def get_client_ip(request):
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
	if x_forwarded_for:
		ip = x_forwarded_for.split(',')[0]
	else:
		ip = request.META.get('REMOTE_ADDR')
	return ip


