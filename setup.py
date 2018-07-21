from setuptools import setup, find_packages


with open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='Flask API Bundle',
    version='0.2.2',
    description='Adds RESTful API support to Flask Unchained',
    long_description=long_description,
    url='https://github.com/briancappello/flask-api-bundle',
    author='Brian Cappello',
    license='MIT',

    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    packages=find_packages(exclude=['docs', 'tests']),
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.6',
    install_requires=[
        'flask-marshmallow>=0.8.0',
        'flask-sqlalchemy-bundle>=0.3.0',
        'flask-unchained>=0.3.0',
        'marshmallow>=2.13.6',
        'marshmallow-sqlalchemy>=0.13.1',
    ],
    entry_points={
        'pytest11': [
            'flask_api_bundle = flask_api_bundle.pytest',
        ],
    },
)
