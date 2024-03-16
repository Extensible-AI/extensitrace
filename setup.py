from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='agent_logger',
    version='0.1.0',
    description='Minimalistic logging utility for monitoring function calls',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Extensible-AI/agent-logger',
    author='Omkaar Kamath, Parth Sareen',
    author_email='omkaar@extensible.dev, parth@extensible.dev',
    license='MIT',
    packages=find_packages(),
    install_requires=[
    ],
)