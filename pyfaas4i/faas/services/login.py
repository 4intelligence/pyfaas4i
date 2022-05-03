from .auth_zero import get_device_code


def login():
    '''
    This function must be called before any interaction with the 4casthub environment.
    It will provide the user with the login steps to use PyFaaS for modelling.
    '''
    print("Initializing authorization flow")
    get_device_code()
    return



