# Services submodule
Functions to allow users to access 4casthub with PyFaaS through 2-factor-authentication. 

## services.login()
**function <span style="color:orange">login</span>()**

This function must be called before any interaction with the 4casthub environment.
It will provide the user with the login steps to use PyFaaS for modelling.


### **Examples**
```python
from pyfaas4i.faas import login
login()
```
By default, the login function will wait 90 seconds for authentication. If you wish to adjust the wait time, it is possible to change the parameter using a numeric value for sleep_time.
---

## services.get_device_code()
**function <span style="color:orange">get_device_code</span>()**

Performs the login flow to allow a user to utilise the APIs from the 4casthub environment.

