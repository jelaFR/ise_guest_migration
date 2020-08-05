try:
    # Module and credentials importation
    import xml.etree.ElementTree as ET  # Parse XML
    import requests                     # Create API request
    import csv                          # Build CSV file
    import urllib3                      # Remove Request warning
    import pickle                       # Freeze vars upon app reboot
    import credentials                  # Import ISE URL and credentials
    from time import time               # Display time in messages
    from tqdm import tqdm               # Display progress bar
    # Remove warning during requests execution
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError as err:
    print("[ERROR] Module importation failed =>", err)
    exit(0)


def get_cisco_ise_guests(which_ise="legacy", user_per_page=100, max_page=0, debug=False):
    """Collect Guest user list

    Args:
        which_ise (str, optional): Defines on which ISE this function will apply ('new' or 'legacy"). Defaults to "legacy".
        user_per_page (int, optional): Number of user to collect per API request (max. 100). Defaults to 100.
        max_page (int, optional): Maximum number of guest to collect before stopping execution (0 is max). Defaults to 0.
        debug (bool, optional): Debug mode to collect execution time information. Defaults to False.

    Returns:
        guest_collected (bool): If the full list of user collected?
        guest_list (list): Guest user list
        guest_count (int): Number of guest user
    """
    # Initiate vars
    page_id = 1 
    guest_list = list()
    guest_collected = False
    guest_count = 0

    # Debug mode (if selected)
    if debug:
        start_time_root = time()
        print("[DEBUG] Debut de la lecture des listes de comptes guest via API sur Cisco ISE")

    while True:
        # Debug mode (if selected)
        if debug:
            start_time = time()
            print(f"[DEBUG] Debut de la lecture des comptes guest sur la page {page_id}")

        # Build itemps required for API request
        headers = {'Accept': 'application/vnd.com.cisco.ise.identity.guestuser.2.0+xml'}
        if which_ise.lower() == "legacy":
            api_url = f"{credentials.LEGACY_ISE_URL}/ers/config/guestuser?page={str(page_id)}&size={user_per_page}"
            try:
                ise_response = requests.get(api_url, auth=(credentials.LEGACY_ISE_LOGIN, credentials.LEGACY_ISE_PASSWORD), verify=False, headers=headers, timeout=(5, 30))
            except requests.ConnectTimeout as err:
                print(f"[ERROR] Cannot connect to {which_ise} with provided IP address : TIMEOUT")
                break
        elif which_ise.lower() == "new":
            api_url = f"{credentials.NEW_ISE_URL}/ers/config/guestuser?page={str(page_id)}&size={user_per_page}"
            try:
                ise_response = requests.get(api_url, auth=(credentials.NEW_ISE_LOGIN, credentials.NEW_ISE_PASSWORD), verify=False, headers=headers, timeout=(5, 30))
            except requests.ConnectTimeout as err:
                print(f"[ERROR] Cannot connect to {which_ise} with provided IP address : TIMEOUT")
                break
        else:
            print("[ERROR] ISE type must be either 'legacy' OR 'new'")
            break

        # ISE response is KO (credentials fails but response given)
        if not ise_response.ok and ise_response.status_code == 401:
            print(f"[WARNING] ISE refused our request => Please check credentials for {which_ise} ISE")
            break
        elif not ise_response.ok:
            print(f"[WARNING] {which_ise} ISE returned status code {ise_response.status_code} during consultation of guest page #{page_id}")
            break

        # Returned XML data processing
        root = ET.fromstring(ise_response.content)
        guest_in_page = root.attrib.get("total","0")
        for child in root:
            for subchild in child:
                guest_list.append(subchild.attrib.get('id',''))
                guest_count += 1

        # Is the max page value reached : yes => break, no => continue
        if (guest_in_page != "0") and ((max_page == 0) or (page_id < max_page)):
            page_id += 1
            # Debug mode
            if debug:
                stop_time = time()
                print(f"[DEBUG] Fin de la lecture des comptes guest sur la page {page_id}, duree : {stop_time - start_time}, total guest= {guest_count}")         
        else:  # break execution of loop if guest list is OK
            guest_collected = True
            break

    # Debug mode
    if debug:
        stop_time_root = time()
        print("[DEBUG] Fin de la lecture des listes de comptes guest via API sur Cisco ISE")
        print(f"[DEBUG] Temps ecoule : {stop_time_root - start_time_root} ")
    
    return guest_collected, guest_list, guest_count


def get_guest_details(guest_id, which_ise="legacy", debug=False):
    """Collect information about guest user in Cisco ISE

    Args:
        guest_id (str): ISE identification of guest user on legacy database
        which_ise (str, optional): Defines on which ISE this function will apply ('new' or 'legacy"). Defaults to "legacy".
        debug (bool, optional): Debug mode to collect execution time information. Defaults to False.

    Returns:
        guest_user_details(dict): Full informations about guest user
        sponsort_username(str): Name of sponsort that create guest user
    """
    while True:
        # Initialise guest dictionary
        guest_user_details = dict()
        guest_user_details["uid"] = guest_id
        guest_user_details["username"] = str()
        guest_user_details["password"] = str()
        guest_user_details["location"] = str()
        guest_user_details["from_date"] = str()
        guest_user_details["to_date"] = str()
        guest_user_details["valid_days"] = str()
        guest_user_details["guest_type"] = str()
        guest_user_details["enabled"] = str()
        guest_user_details["sponsor_username"] = str()

        # Build API Request depending of ISE type (either 'legacy' for OLD ISE or 'new' for NEW ISE)
        headers = {'Accept': 'application/vnd.com.cisco.ise.identity.guestuser.2.0+xml'}
        if which_ise.lower() == "legacy":
            api_url = f"{credentials.LEGACY_ISE_URL}/ers/config/guestuser/{guest_id}"
            try:
                ise_response = requests.get(api_url, auth=(credentials.LEGACY_ISE_LOGIN, credentials.LEGACY_ISE_PASSWORD), verify=False, headers=headers, timeout=5)
            except requests.ConnectTimeout as err:
                print(f"[ERROR] Cannot connect to {which_ise} with provided IP address : TIMEOUT")
                break
        elif which_ise.lower() == "new":
            api_url = f"{credentials.NEW_ISE_URL}/ers/config/guestuser/{guest_id}"
            try:
                ise_response = requests.get(api_url, auth=(credentials.NEW_ISE_LOGIN, credentials.NEW_ISE_PASSWORD), verify=False, headers=headers, timeout=5)
            except requests.ConnectTimeout as err:
                print(f"[ERROR] Cannot connect to {which_ise} with provided IP address : TIMEOUT")
                break
        else:
            print("[ERROR] ISE type must be either 'legacy' OR 'new'")
            break

        # Manage ISE KO response
        if not ise_response.ok:
            print(f"[WARNING] {which_ise} ISE returned status code {ise_response.status_code} during consultation of guest ID #{guest_id}")
            break

        # Returned XML data processing
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
                sponsort_username = child.text
            elif child.tag == "status":
                guest_user_details["status"] = child.text     

        # End of guest details collection
        break

    return guest_user_details, sponsort_username


def guest_to_csv(guest_list, csv_out_file):
    """
    Build a CSV file containing Guest user list exported from legacy and imported to new

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


def check_sponsort_portal(portal_id, which_ise="legacy", debug=False):
    """Check if portal ID exist on ISE

    Args:
        portal_id (str): Portal identifier to check
        which_ise (str, optional): Defines on which ISE this function will apply ('new' or 'legacy"). Defaults to "legacy".
        debug (bool, optional): Debug mode to collect execution time information. Defaults to False.

    Returns:
        portal_exist (bool): True if portal exist
    """
    # Initiate vars
    portal_exist = False

    # Debug mode (if selected)
    if debug:
        start_time_root = time()
        print("[DEBUG] Starting portal collection on remote ISE")

    while True:
        # Build items required for API request
        
        if which_ise.lower() == "legacy":
            headers = {'Accept': 'application/vnd.com.cisco.ise.identity.portal.2.0+xml'}
            api_url = f"{credentials.LEGACY_ISE_URL}/ers/config/sponsorportal/{portal_id}"
            try:
                ise_response = requests.get(api_url, auth=(credentials.LEGACY_ISE_LOGIN, credentials.LEGACY_ISE_PASSWORD), verify=False, headers=headers, timeout=(5, 30))
            except requests.ConnectTimeout as err:
                print(f"[ERROR] Cannot connect to {which_ise} with provided IP address : TIMEOUT")
                break
        elif which_ise.lower() == "new":
            headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
            api_url = f"{credentials.NEW_ISE_URL}/ers/config/sponsorportal/{portal_id}"
            try:
                ise_response = requests.get(api_url, auth=(credentials.NEW_ISE_LOGIN, credentials.NEW_ISE_PASSWORD), verify=False, headers=headers, timeout=(5, 30))
            except requests.ConnectTimeout as err:
                print(f"[ERROR] Cannot connect to {which_ise} with provided IP address : TIMEOUT")
                break
        else:
            print("[ERROR] ISE type must be either 'legacy' OR 'new'")
            break

        # Manage ISE KO response
        if not ise_response.ok:
            print(f"[WARNING] {which_ise} ISE returned status code {ise_response.status_code} during consultation of portal ID #{guest_id}")
            break
        else:
            portal_exist = True
            break

    return portal_exist


def create_guest_user(guest_user_details, which_ise="new", debug=False):
    """Create a guest user on Cisco ISE using API

    Args:
        guest_user_details (dict): Full informations about guest user
        which_ise (str, optional): Defines on which ISE this function will apply ('new' or 'legacy"). Defaults to "legacy".
        debug (bool, optional): Debug mode to collect execution time information. Defaults to False.

    Returns:
        guest_created(bool): Is the guest user created?
    """
    # Initiate vars
    guest_created = False

    # Continue to create user except if an exception occurs
    while True:
        # Build Guest attributes
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
            <portalId>{portal_id}</portalId>\
            <sponsorUserName>{guest_user_details["sponsor_username"]}</sponsorUserName>\
            </ns0:guestuser>'
        
        # Build API Request depending of ISE type (either 'legacy' for OLD ISE or 'new' for NEW ISE)
        headers = {'Content-Type': 'application/vnd.com.cisco.ise.identity.guestuser.2.0+xml; charset=utf-8'}
        if which_ise == "legacy":
            api_url = f"{credentials.LEGACY_ISE_URL}/ers/config/guestuser"
            try:
                ise_response = requests.post(api_url, data=guest_infos, auth=(credentials.LEGACY_ISE_LOGIN, credentials.LEGACY_ISE_PASSWORD), verify=False, headers=headers, timeout=5)
            except requests.ConnectTimeout as err:
                print(f"[ERROR] Cannot connect to {which_ise} with provided IP address : TIMEOUT")
                break        
        elif which_ise == "new":
            api_url = f"{credentials.NEW_ISE_URL}/ers/config/guestuser"
            try:
                ise_response = requests.post(api_url, data=guest_infos, auth=(credentials.NEW_ISE_LOGIN, credentials.NEW_ISE_PASSWORD), verify=False, headers=headers, timeout=5)
            except requests.ConnectTimeout as err:
                print(f"[ERROR] Cannot connect to {which_ise} with provided IP address : TIMEOUT")
                break
        else:
            print("[ERROR] ISE type must be either 'legacy' OR 'new'")
            break

        # Manage ISE KO response
        if not ise_response.ok:
            print(f"[WARNING] {which_ise} ISE returned status code {ise_response.status_code} during creation of guest ID #{guest_id}")
            break
        else:
            guest_created = True  # Success of guest creation
            break

    return guest_created


def main():
    """
    Main code execution
    """
    # Initiate vars
    # TODO: Pickle some vars to allow multiple code execution
    csv_out = "guest_list.csv"
    sponsort_user_list = list()
    debug_mode = True
    guest_id_collected = False  # True if guest ID list is sucessfully collected at Step 2
    guest_pages = 1  # Number of guest page to parse (0 => max)
    guest_user_list = list()
    guest_failed_user_list = list()

    # Step 1 : Test ISE connection
    legacy_conn_ok, _, _  =  get_cisco_ise_guests(which_ise="legacy", max_page=1, user_per_page=1)
    new_conn_ok, _, _ = get_cisco_ise_guests(which_ise="new", max_page=1, user_per_page=1)
    if legacy_conn_ok is False:
        exit(0)
    elif new_conn_ok is False:
        exit(0)

    # Step 2 : Collect guest ID on legacy ISE
    if not guest_id_collected:
        guest_id_collected, guest_id_list, guest_count = get_cisco_ise_guests(max_page=guest_pages, debug=debug_mode)

    # Step 3 : Collect guest informations on legacy ISE and sponsort user list
    for guest_id in tqdm(guest_id_list):
        guest_details, sponsort_username = get_guest_details(guest_id, debug=debug_mode) # Collect Guest details on legacy ISE
        if sponsort_username not in sponsort_user_list:  # Collect sponsort for later use
            sponsort_user_list.append(sponsort_username)
        guest_user_list.append(guest_details)

    # Step 4 : Write all guest information inside CSV file
    guest_to_csv(guest_user_list, csv_out)

    # Step 5 : Check if sponsort usernames and portal id exists on new ISE
    portal_ok = check_sponsort_portal(credentials.NEW_ISE_PORTAL_ID, which_ise="new")
    if not portal_ok:
        exit(0)
    # TODO : Implement function to check if sponsort_users are created

    # Step 6 : Inject guest users inside new ISE
    for guest_details in guest_user_list:
        created = create_guest_user(guest_details, debug=debug_mode)
        if not created:
            guest_failed_user_list.append(guest_details)


if __name__ == "__main__":
    """Code called during execution
    """
    try:
        main()
    except KeyboardInterrupt:
        print("[DEBUG] Stopping code excution due to user request")
    except:
        print("[ERROR] Unknown exception has occured")