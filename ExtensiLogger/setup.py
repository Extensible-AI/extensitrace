from setuptools import setup, find_packages

# Ensure the 'requirements.txt' file is read correctly to list all dependencies.
with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='extensilogger',  # Make sure this is a unique name for PyPI if you plan to publish.
    version='0.1',  
    packages=find_packages(), # This automatically finds packages in your project.
    install_requires=required,  # List of dependencies read from 'requirements.txt'.
    # package_dir={'': 'extensilogger'},
    author='Parth Sareen, Omkaar Kamath',  # Update with the correct author's name.
    author_email='parth@extensible.dev, omkaar@extensible.dev',  # Update with the correct author email.
    description='A logger for tracking your agent workflow',  # A brief description of your project.
    url='https://github.com/Extensible-AI/agent-logger-python',  # Update with the correct URL.
    # Consider adding classifiers to provide more metadata about your package.
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',  # Specify the Python versions your project supports.
)