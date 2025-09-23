import setuptools

with open('requirements.txt') as f:
    required = f.read().splitlines()
setuptools.setup(
    name='pyfaas4i',
    version='1.9.0',
    packages=setuptools.find_packages(),
    author='4intelligence',
    author_email='n.araujo@4intelligence.ai',
    description='Using FaaS in Python',
    install_requires=required,
    package_data={'':['*.R', '*.ini']},
    include_package_data=True
)
