"""Operator-selected WSPR acceptance: the independently decoded expected message."""
EXPECTED=('AA0NT','EM18','37')


def assess(report,receipt,stdout):
    matches=[line for line in stdout.splitlines() if len(line.split())==8 and tuple(line.split()[-3:])==EXPECTED]
    issues=[]
    if type(receipt.get('returncode')) is not int or receipt['returncode']!=0:issues.append('external decoder did not complete successfully')
    if report.get('decoded') is not True or receipt.get('decoded') is not True or not matches:issues.append('expected message was not independently decoded')
    if receipt.get('matches')!=matches:issues.append('decoder receipt differs from actual stdout')
    return dict(schema='phase14-wspr-decode-acceptance/1',passed=not issues,issues=issues,
        expected=list(EXPECTED),matches=matches,legacy_screen_passed=report.get('passed'),
        operator_amendment='2026-10-09: WSPR passes when the external tool decodes the expected transmission.',
        method='Successful external wsprd exit and exact expected callsign/grid/power in retained decoder stdout; drift/residual measurements remain diagnostics.')
