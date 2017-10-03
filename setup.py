from setuptools import setup

setup(name='PandaBot',
	version='1.2',
	author='Benjamin J. C. Reeve',
	author_email='benreeve99@yahoo.co.uk',
	packages=['PandaBot'],
	install_requires=['discord.py'],
	dependency_links = ['https://github.com/Rapptz/discord.py']
)