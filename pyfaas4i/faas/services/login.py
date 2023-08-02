from .auth_zero import get_device_code
from .._utilities import _get_proxies


def login(sleep_time=90,
          **kwargs):
    '''
    This function must be called before any interaction with the 4casthub environment.
    It will provide the user with the login steps to use PyFaaS for modelling.
    Args:
        sleep_time: Maximum waiting for URI authentication (in secs)
    '''

    # Avoiding 1 or less second sleep_time
    if sleep_time <= 1:
        sleep_time = 2

    print("Initializing authorization flow")
    if any([x not in ['proxy_url', 'proxy_port'] for x in list(kwargs.keys())]):
        unexpected = list(kwargs.keys())
        for arg in ['proxy_url', 'proxy_port']:
            if arg in list(kwargs.keys()):
                unexpected.remove(arg)

        raise TypeError(f'login() got an unexpected keyword argument: {", ".join(unexpected)}')
    proxy_url = None
    proxy_port = None

    if 'proxy_url' in kwargs:
        proxy_url = kwargs['proxy_url']

    if 'proxy_port' in kwargs:
        proxy_port = kwargs['proxy_port']

    # ----- Get proxies (if any)
    proxies = _get_proxies(proxy_url=proxy_url,
                           proxy_port=proxy_port)

    get_device_code(sleep_time,
                    proxies=proxies)
    return
