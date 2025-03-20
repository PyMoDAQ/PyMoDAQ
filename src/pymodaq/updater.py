import argparse
import subprocess
import sys
import time
import logging

from pathlib import Path

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))
logger.addHandler(logging.StreamHandler(sys.stdout))

def wait_for_parent():
	'''
		A function to wait for its parent to terminate execution.

		In order to achieve that, this process has to be started with
		stdin replaced by a piped stream from its parent. When the
		parent terminates, stdin will close and either return from read
		or throw an exception. De facto creating a way to wait for its
		parent's termination.

		It then sleep for 2 seconds, to let the parent process complete
		termination.

		CAUTION: If the process was not started by piping stdin AND 
		the --wait option is set, this function will hang forever.

		We could use `psutil` or a similar lib to check for parent's process
		existance with its pid. 
	'''

	logger.info("Waiting for parent process to stop.")
	try:
		sys.stdin.read()
	except:
		pass
	logger.debug("Parent process closed stdin")
	time.sleep(2)
	logger.info("Parent process stopped.")

def process_args():
	'''
		Declare arguments for updater.py, parse them and returns them in an object.
		The arguments are:
			--file <file> to request a python program to (re)start after update if needed (optional) 
			--wait        to wait for the starting process to terminate before updating (optional, defaults to False)
			packages      the package list to install/update (they should contain the version in a pip accepted format)
	'''
	parser = argparse.ArgumentParser(description='Update pymodaq using pip.')
	parser.add_argument('--file', type=str,  help='the pymodaq script to restart after update')
	parser.add_argument("--wait", action="store_true", help="enable waiting for pymodaq to finish mode (default is disabled).")
	parser.add_argument('packages', type=str, nargs='+', help='package list')
	return parser.parse_args()

def restart_if_command_launch(args):
	'''
		Try to detect if this process if launched using the declared command (i.e. `pymodaq_updater`)
		or using the script file (`updater.py`). If it uses the command, it restart the process to
		force it to use the script file, thus preventing a locked file during update on windows systems.
	'''
	python_file_path = Path(__file__) # Should be the path to `updater.py`
	started_path = Path(sys.argv[0])  # Either `updater.py` or `pymodaq_updater`
	
	# If they're different we'll restart using the script file
	if started_path.absolute() != python_file_path.absolute():
		logger.info("Started as pymodaq_updater, need to restart using python to prevent lock.")
		# We HAVE to wait for this process to stop in the restarted process
		new_args = ['--wait'] + sys.argv[1:]
		if args.wait:
			wait_for_parent()
	
		subprocess.Popen([sys.executable, str(python_file_path.absolute())] + new_args,  stdin=subprocess.PIPE)
		sys.exit(0)

def main():
	args = process_args()
	logger.info(f"Arguments processed: {args}")

	restart_if_command_launch(args)

	if args.wait:
		wait_for_parent()

	packages_str = ', '.join(args.packages)
	logger.info(f'Updating packages: {packages_str}')
	
	with subprocess.Popen([sys.executable, '-m', 'pip', 'install'] + args.packages, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as pip:
		for line in pip.stdout:
			# Can't decode as some characters are not valid and make the whole process fail
			logger.info(line[:-1])
	ret_code = pip.wait()
	

	if ret_code == 0:
		logger.info(f'Succesfully updated {packages_str}')
	else:
		logger.error(f'Error while updating {packages_str}, pip returned {ret_code}')

	if args.file is not None:
		logger.info(f"Restarting {args.file} script after update.")
		subprocess.Popen([sys.executable, args.file])


if __name__ == "__main__":
	main()