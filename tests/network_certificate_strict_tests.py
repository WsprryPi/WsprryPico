#!/usr/bin/env python3
"""Real strict chain validation; temporary credentials only."""
import importlib.util,subprocess,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('certificates',Path(__file__).parents[1]/'scripts/network_certificates.py')
cert=importlib.util.module_from_spec(spec);spec.loader.exec_module(cert)
class Tests(unittest.TestCase):
 def test_strict_server_client_and_missing_identifier_rejection(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);ca=root/'ca';client=root/'client'
   cert.main(['init','--directory',str(ca),'--device','test','--address','127.0.0.1'])
   cert.main(['issue-client','--ca-directory',str(ca),'--name','operator','--output',str(client)])
   for path,purpose in ((ca/'server/server.crt','sslserver'),(client/'client.crt','sslclient')):
    result=subprocess.run(['openssl','verify','-x509_strict','-purpose',purpose,'-CAfile',str(ca/'client-ca.crt'),str(path)],capture_output=True)
    self.assertEqual(result.returncode,0,result.stderr)
   # Re-sign the same key/identity with the legacy missing identifiers.
   req=root/'old.csr';ext=root/'old.ext';old=root/'old.crt'
   cert.openssl('req','-new','-key',ca/'server/server.key','-subj','/CN=test','-out',req)
   ext.write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectAltName=IP:127.0.0.1\nsubjectKeyIdentifier=none\nauthorityKeyIdentifier=none\n')
   cert.openssl('x509','-req','-in',req,'-CA',ca/'client-ca.crt','-CAkey',ca/'ca.key','-set_serial','123','-days','1','-extfile',ext,'-out',old)
   result=subprocess.run(['openssl','verify','-x509_strict','-CAfile',str(ca/'client-ca.crt'),str(old)],capture_output=True)
   self.assertNotEqual(result.returncode,0);self.assertIn(b'Missing Authority Key Identifier',result.stderr)
   (ca/'server/server.crt').write_bytes(old.read_bytes())
   with self.assertRaises(RuntimeError):cert.validate_bundle(ca/'server')
if __name__=='__main__':unittest.main()
