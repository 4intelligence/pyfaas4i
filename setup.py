import setuptools

with open('requirements.txt') as f:
    required = f.read().splitlines()
setuptools.setup(
    name='pyfaas4i',
    version='1.5.1',
    packages=setuptools.find_packages(),
    author='4intelligence',
    author_email='pedro.zaterka@4intelligence.com.br',
    description='Using FaaS in Python',
    install_requires=required,
    package_data={'':['*.R', '*.ini']},
    include_package_data=True
)
