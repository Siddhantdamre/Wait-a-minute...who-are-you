import subprocess
with open('c6_direct_out.txt', 'w') as f:
    result = subprocess.run(['python', 'tests/test_golden_c6.py'], capture_output=True, text=True)
    f.write(result.stdout)
    f.write('\nErrors:\n')
    f.write(result.stderr)
