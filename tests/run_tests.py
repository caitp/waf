#!/usr/bin/env python

import os, sys, subprocess

tests_dir = os.path.dirname(os.path.abspath(__file__))
waf = os.path.abspath(os.path.join(tests_dir, '..', 'waf'))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(waf))))

from multiprocessing import Process, Manager
from waflib import Logs

Logs.init_log()

# List of "tests/<name>" strings indicating a test to skip. The name represents
# the directory of the test.
kSkippedTests = [
]

# By default, tests use 'distclean configure build', but can be configured to
# use different commands here.
kDefaultTestCommands = 'distclean configure build'
kTestCommands = {
	'tests/apis': 'distclean configure test'
}

kColors = {
	'$red': 'RED',
	'$green': 'GREEN',
	'$gray': 'GRAY',
	'$yellow': 'YELLOW',
	'$off': 'NORMAL'
}

def _get(o, key, default):
	try: return o[key]
	except: return default

def _print(*kArgs):
	color = 'NORMAL'
	label = ''
	for arg in kArgs:
		arg = str(arg)
		try:
			color = kColors[arg]
		except:
			label = arg
			Logs.pprint(color, label, sep='')
	Logs.pprint('', '') #Line terminator

def run_test(test_dir, state, retryTests):
	test_name = 'tests/{0}'.format(os.path.basename(test_dir))
	if (test_name in state['skippedTests']):
		_print('$gray', '[SKIP] %s' % test_name)
		state['skipped'] += 1
		return

	commands = _get(kTestCommands, test_name, kDefaultTestCommands)
	args = ("%s %s %s" % (sys.executable, waf, commands)).split()
	p = subprocess.Popen(args, cwd=test_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	p.wait()

	if p.returncode != 0:
		retryTests.append(test_dir)
		if state['retrying']:
			return
		status = 'FAIL'
	elif state['retrying']:
		status = 'FLAKE'
	else:
		status = 'PASS'

	if state['retrying']:
		# If flaked, increase passes and decrease failures
		state['failed'] -= 1
		state['passed'] += 1
	else:
		# Otherwise, increase passes if passed, and failures if failed
		state['passed' if p.returncode == 0 else 'failed'] += 1

	error = '' if p.returncode == 0 else '\n%s' % '\n'.join(
			['    > %s' % line for line in p.stdout.read().splitlines()])
	if status is 'PASS':
		_print('$green', '[PASS]  %s' % test_name)
	elif status is 'FLAKE':
		_print('$yellow', '[FLAKE] %s' % test_name)
	else:
		_print('$red', '[FAIL]  %s\n%s\n\n%s\n' % (test_name, '\n'.join(
				['    > %s' % line for line in p.stdout.read().splitlines()]), '\n'.join(
				['    > %s' % line for line in p.stderr.read().splitlines()])))

def noop_onexit(status, **stats):
	pass

def run_all_tests(dir, **kwArgs):
	# All root wscripts under /tests
	tests = [os.path.join(tests_dir, dir) for dir in next(os.walk(tests_dir))[1]];
	skippedTests = getattr(kwArgs, 'skippedTests', kSkippedTests)
	onFinished = _get(kwArgs, 'onExit', noop_onexit)

	total = len(tests)

	manager = Manager()
	state = manager.dict()
	state['skippedTests'] = skippedTests
	state['passed'] = 0
	state['failed'] = 0
	state['skipped'] = 0
	retryTests = manager.list()
	state['retrying'] = False

	processes = []
	for test in tests:
		if (os.path.exists(os.path.join(test, 'wscript'))):
			p = Process(target=run_test, args=(test, state, retryTests))
			p.start()
			processes.append(p)

	for p in processes:
		p.join()

	retry = _get(kwArgs, 'retry', 0)
	while retry > 0 and len(retryTests) > 0:
		retry -= 1
		tests = retryTests
		retryTests = manager.list()
		state['retrying'] = True
		processes = []
		for test in tests:
			p = Process(target=run_test, args=(test, state, retryTests))
			p.start()
			processes.append(p)
		for p in processes:
			p.join()

	if state['failed'] < 0:
		state['failed'] = 0

	onFinished(state['failed'] == 0,
		passed=state['passed'],
		failed=state['failed'],
		skipped=state['skipped'],
		total=total)

def testSummary(status, **kwArgs):
	passed = kwArgs['passed']
	failed = kwArgs['failed']
	skipped = kwArgs['skipped']
	total = passed + failed + skipped

	def percent(numerator, denominator, places):
		formatted = format(100 * float(numerator) / float(denominator), '.%df' % places)
		return formatted.rjust(4 + places, ' ')

	status_name = 'PASS' if status else 'FAIL'
	status_color = '$green' if status else '$red'
	_print()
	_print(status_color, '[%s] ' % status_name,
			'$green', passed, '$off', '/ ',
			'$red', failed, '$off', '/ ',
			'$gray', skipped, '\n\n',
			'$green', '  Passed: %s%%\n' % percent(passed, total, 2),
			'$red', '  Failed: %s%%\n' % percent(failed, total, 2),
			'$gray', ' Skipped: %s%%\n' % percent(skipped, total, 2))

	sys.exit(0 if status else 1)

def main():
	run_all_tests(tests_dir, onExit=testSummary, skippedTests=kSkippedTests, retry=10)

if __name__ == "__main__":
	main()
