from zoho import *
from books.model.Contact import Contact
from books.model.ContactPerson import ContactPerson
from books.model.Address import Address
from books.exception.BooksException import BooksException


contact_api = zoho_books.get_contacts_api()


def create_customer(contact_name, contact_person, phone, address1, city, state, gst_no=None, address2=''):
    contact_person_obj = ContactPerson()
    contact_person_obj.mobile = phone
    splits = contact_person.split(' ', 1)
    contact_person_obj.first_name = splits[0]
    if len(splits) > 1:
        contact_person_obj.last_name = splits[1]
    contact_person_obj.set_is_primary_contact(True)
    address = Address()
    address.set_city(city)
    address.set_address(address1)
    address.set_street_address1(address2[:100])
    address.set_state(state)
    address.set_country('India')
    contact = Contact()
    contact.set_contact_persons([contact_person_obj])
    contact.set_contact_name(contact_name)
    contact.set_place_of_contact(state_info[state][1])
    contact.set_company_name(contact_name)
    contact.set_billing_address(address)
    contact.set_shipping_address(address)
    contact.set_contact_type('customer')
    if gst_no:
        contact.set_gst_treatment('business_gst')
        contact.set_gst_no(gst_no.upper())
    else:
        contact.set_gst_treatment('business_none')
    # print(json.dumps(contact.to_json()))
    try:
        contact_api.create(contact)
    except BooksException as e:
        print('Warning: Failed to create customer: {} because of error: {} - {}'.format(contact_name, e.code, e.message))
        return False
    return True

