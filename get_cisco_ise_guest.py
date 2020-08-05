# Module importation
try:
    import xml.etree.ElementTree as ET  # Parse XML
    import requests                     # Create API request
    import csv                          # Build CSV file
    import urllib3                      # Remove Request warning
    import pickle                       # Freeze vars upon app reboot
    import ise_credentials              # Import ISE URL and credentials
    from time import time               # Display time in messages
    from tqdm import tqdm               # Display progress bar
    # Remove warning during requests execution
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError as err:
    print("[ERROR]", err)
finally:
    print("[ERROR] Module importation failed")
    exit(0)


def get_cisco_ise_portals(url, login, password):
    """Collect list of Cisco ISE portals list
    Args:
        url (str): Cisco ISE base URL (without /)
        login (str): Cisco ISE username (requires to be member of Sponsort Group)
        password (str): Password

    """

    # Connect to ISE
    new_url = f"{url}/ers/config/portal/"
    headers = {'Accept': 'application/vnd.com.cisco.ise.identity.portal.2.0+xml', 'Content-Type': 'application/vnd.com.cisco.ise.identity.portal.2.0+xml'}
    ise_response = requests.get(new_url, auth=(login, password), verify=False, headers=headers)

    # Data processing
    root = ET.fromstring(ise_response.content)
    guest_in_page = root.attrib.get("total","0")
    for child in root:
        for subchild in child:
            guest_list.append(subchild.attrib.get('id',''))
            guest_count += 1

    return guest_list, guest_count


def get_cisco_ise_guests(url, login, password, max_page=0, debug=False):
    """Collect guest user list

    Args:
        url (str): Cisco ISE base URL
        login (str): Cisco ISE username (requires to be member of Sponsort Group)
        password (str): Password
        

    Returns:
        guest_list (list): Id of guest users
        guest_count (int): Total amount of guest users
    """

    # Initiate vars
    page_id = 1 
    guest_list = list()
    guest_count = 0

    if debug:
        start_time_root = time()
        print("[DEBUG] Debut de la lecture des listes de comptes guest via API sur Cisco ISE")

    while True:
        # Connect to ISE
        if debug:
            start_time = time()
            print(f"[DEBUG] Debut de la lecture des comptes guest sur la page {page_id}")
        # Remove "/" at the end of URL
        url = url.rstrip("/")
        # Build itemps required for API request
        new_url = f"{url}/ers/config/guestuser?page={str(page_id)}&size=100"  # 100 items returned per request
        headers = {'Accept': 'application/vnd.com.cisco.ise.identity.guestuser.2.0+xml'}
        ise_response = requests.get(new_url, auth=(login, password), verify=False, headers=headers)

        # Data processing
        root = ET.fromstring(ise_response.content)
        guest_in_page = root.attrib.get("total","0")
        for child in root:
            for subchild in child:
                guest_list.append(subchild.attrib.get('id',''))
                guest_count += 1

        # Continue if there is more than 1 guest
        if (guest_in_page != "0") and ((max_page == 0) or (page_id < max_page)):
            # Debug mode
            if debug:
                stop_time = time()
                print(f"[DEBUG] Fin de la lecture des comptes guest sur la page {page_id}, duree : {stop_time - start_time}, total guest= {guest_count}")
            page_id += 1
        # break execution of loop if guest list is OK
        else:
            break
        pass

    # Debug mode
    if debug:
        stop_time_root = time()
        print("[DEBUG] Fin de la lecture des listes de comptes guest via API sur Cisco ISE")
        print(f"[DEBUG] Temps ecoule : {stop_time_root - start_time_root} ")
    
    return guest_list, guest_count


def get_guest_details(url, login, password, guest_user, debug=False):
    """
    Collect information about guest user in Cisco ISE

    Args:
        url (str): Cisco ISE base URL (without /)
        login (str): Cisco ISE username (requires to be member of Sponsort Group)
        password (str): Password   
        guest_user (str): Guest user ID

    Returns:
        guest_user_details (dict): Guest_users details (ordered in dict)
    """

    # Initialise guest dictionary
    guest_user_details = dict()
    guest_user_details["uid"] = guest_user
    guest_user_details["username"] = str()
    guest_user_details["password"] = str()
    guest_user_details["location"] = str()
    guest_user_details["from_date"] = str()
    guest_user_details["to_date"] = str()
    guest_user_details["valid_days"] = str()
    guest_user_details["guest_type"] = str()
    guest_user_details["enabled"] = str()
    guest_user_details["sponsor_username"] = str()

    # Connect to ISE
    new_url = f"{url}/ers/config/guestuser/{guest_user}"
    headers = {'Accept': 'application/vnd.com.cisco.ise.identity.guestuser.2.0+xml'}
    ise_response = requests.get(new_url, auth=(login, password), verify=False, headers=headers)

    # Data processing
    root = ET.fromstring(ise_response.content)
    for child in root:
        if child.tag == "guestAccessInfo":
            for subchild in child:
                if subchild.tag == "fromDate":
                    guest_user_details["from_date"] = subchild.text
                elif subchild.tag == "toDate":
                    guest_user_details["to_date"] = subchild.text
                elif subchild.tag == "validDays":
                    guest_user_details["valid_days"] = subchild.text
                elif subchild.tag == "location":
                    guest_user_details["location"] = subchild.text
        elif child.tag == "guestInfo":
            for subchild in child:
                if subchild.tag == "enabled":
                    guest_user_details["enabled"] = subchild.text
                elif subchild.tag == "password":
                    guest_user_details["password"] = subchild.text
                elif subchild.tag == "userName":
                    guest_user_details["username"] = subchild.text
        elif child.tag == "guestType":
            guest_user_details["guest_type"] = child.text
        elif child.tag == "sponsorUserName":
            guest_user_details["sponsor_username"] = child.text
        elif child.tag == "status":
            guest_user_details["status"] = child.text     

    return guest_user_details


def create_guest_user(url, login, password, guest_user_details):
    """
    Create a guest user on Cisco ISE using API
    """
    # Connect to ISE
    new_url = f"{url}/ers/config/guestuser"
    headers = {'Content-Type': 'application/vnd.com.cisco.ise.identity.guestuser.2.0+xml; charset=utf-8'}
    guest_infos = f'<?xml version="1.0" encoding="UTF-8"?>\
    <ns0:guestuser xmlns:ns0="identity.ers.ise.cisco.com" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:ns1="ers.ise.cisco.com" xmlns:ers="ers.ise.cisco.com" description="ERS Example user " id="123456" name="{guest_user_details["username"]}">\
    <customFields/>\
    <guestAccessInfo>\
        <fromDate>{guest_user_details["from_date"]}</fromDate>\
        <location>{guest_user_details["location"]}</location>\
        <toDate>{guest_user_details["to_date"]}</toDate>\
        <validDays>{guest_user_details["valid_days"]}</validDays>\
    </guestAccessInfo>\
    <guestInfo>\
        <enabled>{guest_user_details["enabled"]}</enabled>\
        <password>{guest_user_details["password"]}</password>\
        <userName>guest{guest_user_details["username"]}</userName>\
    </guestInfo>\
    <guestType>{guest_user_details["guest_type"]}</guestType>\
    <portalId>274a95f0-2e58-11e9-98fb-0050568775a3</portalId>\
    <sponsorUserName>{guest_user_details["sponsor_username"]}</sponsorUserName>\
    </ns0:guestuser>'
    ise_response = requests.post(new_url, data=guest_infos, auth=(login, password), verify=False, headers=headers)

    print(ise_response.text)


def guest_to_csv(guest_list, csv_out_file):
    """
    Convert Guest users details in CSV format

    Args:
        guest_list (list): List of guest users ordered in dicts
        csv_out_file (str): Name of CSV out filename
    """
    csv_columns = ["username", "password", "uid", "enabled", "status", "from_date",\
         "to_date", "valid_days", "location", "guest_type", "sponsor_username"]

    try:
        with open(csv_out_file, 'w', newline='\n', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for data in guest_list:
                writer.writerow(data)
    except IOError:
        print("I/O error")


if __name__ == "__main__":
    # Initiate vars
    csv_out = "filename.csv"
    debug_mode = True
    guest_pages = 0  # Max number of guest page (x100 guest per page) [0 = unlimited]
    guest_user_list = list()

    # Get portal list
    portal_list = get_cisco_ise_portals(ise_url, ise_login, ise_password)

    # Get user list
    guest_list, guest_count = get_cisco_ise_guests(ise_url, ise_login, ise_password, guest_pages, debug_mode)

    # Get guest informations
    for guest_user in tqdm(guest_list):
        guest_details = get_guest_details(ise_url, ise_login, ise_password, guest_user, debug_mode)
        guest_user_list.append(guest_details)
        create_guest_user(new_ise_url, new_ise_login, new_ise_password, guest_details)

    # Format output to CSV
    guest_to_csv(guest_user_list, csv_out)
