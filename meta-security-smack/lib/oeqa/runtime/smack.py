import unittest
import re
import os
import string
from oeqa.oetest import oeRuntimeTest, skipModule
from oeqa.utils.decorators import *

def get_files_dir():
    """Get directory of supporting files"""
    pkgarch = oeRuntimeTest.tc.d.getVar('MACHINE', True)
    deploydir = oeRuntimeTest.tc.d.getVar('DEPLOY_DIR', True)
    return os.path.join(deploydir, "files", "target", pkgarch)

MAX_LABEL_LEN = 255
LABEL = "a" * MAX_LABEL_LEN

def setUpModule():
    if not oeRuntimeTest.hasFeature('smack'):
        skipModule(
            "smack module skipped: "
            "target doesn't have smack in DISTRO_FEATURES")

class SmackBasicTest(oeRuntimeTest):
    ''' base smack test '''
    def setUp(self):
        status, output = self.target.run(
            "grep smack /proc/mounts | awk '{print $2}'")
        self.smack_path = output
        self.files_dir = os.path.join( 
            os.path.abspath(os.path.dirname(__file__)), 'files')
        self.uid = 1000
        status,output = self.target.run("cat /proc/self/attr/current")
        self.current_label = output.strip()

class SmackAccessLabel(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_add_access_label(self):
        ''' Test if chsmack can correctly set a SMACK label '''
        filename = "/tmp/test_access_label"
        self.target.run("touch %s" %filename)
        status, output = self.target.run("chsmack -a %s %s" %(LABEL, filename))
        self.assertEqual(
            status, 0, 
            "Cannot set smack access label. "
            "Status and output: %d %s" %(status, output))                  
        status, output = self.target.run("chsmack %s" %filename)
        self.target.run("rm %s" %filename)
        m = re.search('(?<=access=")\S+(?=")', output)
        if m is None:
            self.fail("Did not find access attribute")
        else:
            label_retrieved = m .group(0)
            self.assertEqual(
                LABEL, label_retrieved, 
                "label not set correctly. expected and gotten: "
                "%s %s" %(LABEL,label_retrieved))
    
class SmackExecLabel(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_add_exec_label(self):
        '''Test if chsmack can correctly set a SMACK Exec label'''
        filename = "/tmp/test_exec_label"
        self.target.run("touch %s" %filename)
        status, output = self.target.run("chsmack -e %s %s" %(LABEL, filename))
        self.assertEqual(
            status, 0, 
            "Cannot set smack exec label. " 
            "Status and output: %d %s" %(status, output))                  
        status, output = self.target.run("chsmack %s" %filename) 
        self.target.run("rm %s" %filename)
        m= re.search('(?<=execute=")\S+(?=")', output)
        if m is None:
            self.fail("Did not find execute attribute")
        else:  
            label_retrieved = m.group(0)
            self.assertEqual(
                LABEL, label_retrieved, 
                "label not set correctly. expected and gotten: " +
                "%s %s" %(LABEL,label_retrieved))

class SmackMmapLabel(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_add_mmap_label(self):
        '''Test if chsmack can correctly set a SMACK mmap label'''
        filename = "/tmp/test_exec_label"
        self.target.run("touch %s" %filename)
        status, output = self.target.run("chsmack -m %s %s" %(LABEL, filename))
        self.assertEqual(
            status, 0, 
            "Cannot set smack mmap label. "
            "Status and output: %d %s" %(status, output))          
        status, output = self.target.run("chsmack %s" %filename)
        self.target.run("rm %s" %filename)
        m = re.search('(?<=mmap=")\S+(?=")', output)
        if m is None:
            self.fail("Did not find mmap attribute")
        else:
            label_retrieved = m.group(0)
            self.assertEqual(
                LABEL, label_retrieved, 
                "label not set correctly. expected and gotten: " +
                "%s %s" %(LABEL,label_retrieved))

class SmackTransmutable(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_add_transmutable(self):
        '''Test if chsmack can correctly set a SMACK transmutable mode'''
        
        directory = "~/test_transmutable"
        self.target.run("mkdir -p %s" %directory)    
        status, output = self.target.run("chsmack -t %s" %directory)
        self.assertEqual(status, 0, "Cannot set smack transmutable. "
                        "Status and output: %d %s" %(status, output))  
        status, output = self.target.run("chsmack %s" %directory)
        self.target.run("rmdir %s" %directory)
        m = re.search('(?<=transmute=")\S+(?=")', output)
        if m is None:
            self.fail("Did not find transmute attribute")
        else:
            label_retrieved = m.group(0)
            self.assertEqual(
                "TRUE", label_retrieved, 
                "label not set correctly. expected and gotten: " +
                "%s %s" %(LABEL,label_retrieved))

class SmackChangeSelfLabelPrivilege(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_privileged_change_self_label(self):
        '''Test if privileged process (with CAP_MAC_ADMIN privilege)
        can change its label.
        
        test needs to change the running label of the current process, 
        so whole test takes places on image
        '''
        status, output = self.target.run(
            "ls /tmp/test_privileged_change_self_label.sh")
        if status != 0:
            self.target.copy_to( 
                os.path.join(
                    self.files_dir,
                    'test_privileged_change_self_label.sh'), 
                "/tmp/test_privileged_change_self_label.sh")

        status, output = self.target.run(
            "bash /tmp/test_privileged_change_self_label.sh")
        self.assertEqual(status, 0, output)

class SmackChangeSelfLabelUnprivilege(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_unprivileged_change_self_label(self):
        '''Test if unprivileged process (without CAP_MAC_ADMIN privilege) 
        cannot change its label'''

        status, echo = self.target.run("which echo")

        status, output = self.target.run("ls /tmp/notroot.py")
        if status != 0:
            self.target.copy_to(
                os.path.join(self.files_dir, 'notroot.py'), 
                "/tmp/notroot.py")

        status, output = self.target.run(
            "python /tmp/notroot.py %d %s %s %s" 
            %(self.uid, self.current_label, echo, LABEL) +
            " 2>&1 >/proc/self/attr/current " +
            "| grep 'Operation not permitted'" )

        self.assertEqual(
            status, 0, 
            "Unprivileged process should not be able to change its label")


class SmackChangeFileLabelPrivilege(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_unprivileged_change_file_label(self):
        '''Test if unprivileged process cannot change file labels'''

        status, chsmack = self.target.run("which chsmack")
        status, touch = self.target.run("which touch")
        filename = "/tmp/test_unprivileged_change_file_label"

        status, output = self.target.run("ls /tmp/notroot.py")
        if status != 0:
            self.target.copy_to(
                os.path.join(self.files_dir, 'notroot.py'), 
                "/tmp/notroot.py")

        self.target.run("python /tmp/notroot.py %d %s %s %s" %(self.uid, self.current_label, touch, filename))
        status, output = self.target.run(
            "python /tmp/notroot.py " +
            "%d unprivileged %s -a %s %s 2>&1 " %(self.uid, chsmack, LABEL, filename) +
            "| grep 'Operation not permitted'"  )

        self.target.run("rm %s" %filename)
        self.assertEqual(
            status, 0, 
            "Unprivileged process changed label for %s" %filename)

class SmackLoadRule(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_load_smack_rule(self):
        '''Test if new smack access rules can be loaded'''

        # old 23 character format requires special spaces formatting
        #      12345678901234567890123456789012345678901234567890123
        ruleA="TheOne                  TheOther                rwxat"
        ruleB="TheOne                  TheOther                r----"
        clean="TheOne                  TheOther                -----"
        modeA = "rwxat"
        modeB = "r"

        status, output = self.target.run(
            'echo -n "%s" > %s/load' %(ruleA, self.smack_path))
        status, output = self.target.run(
            'cat %s/load | grep "^TheOne" | grep " TheOther "' %self.smack_path)
        self.assertEqual(status, 0, "Rule A was not added")  
        mode = filter(bool, output.split(" "))[2].strip()
        self.assertEqual(
            mode, modeA, 
            "Mode A was not set correctly; mode: %s" %mode)

        status, output = self.target.run(
            'echo -n "%s" > %s/load' %(ruleB, self.smack_path))
        status, output = self.target.run(
            'cat %s/load | grep "^TheOne" | grep " TheOther "' %self.smack_path)
        mode = filter(bool, output.split(" "))[2].strip()
        self.assertEqual(
            mode, modeB, 
            "Mode B was not set correctly; mode: %s" %mode)

        self.target.run('echo -n "%s" > %s/load' %(clean, self.smack_path))


class SmackOnlycap(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_smack_onlycap(self):
        '''Test if smack onlycap label can be set

        test needs to change the running label of the current process,
        so whole test takes places on image
        '''
        status, output = self.target.run("ls /tmp/test_smack_onlycap.sh")
        if status != 0:
            self.target.copy_to(
                os.path.join(self.files_dir, 'test_smack_onlycap.sh'),
                "/tmp/test_smack_onlycap.sh")

        status, output = self.target.run("bash /tmp/test_smack_onlycap.sh")
        self.assertEqual(status, 0, output)

class SmackNetlabel(SmackBasicTest):
    @skipUnlessPassed('test_ssh')
    def test_smack_netlabel(self):

        test_label="191.191.191.191 TheOne"
        expected_label="191.191.191.191/32 TheOne"
        
        status, output = self.target.run(
            "echo -n '%s' > %s/netlabel" %(test_label, self.smack_path))
        self.assertEqual(
            status, 0, 
            "Netlabel /32 could not be set. Output: %s" %output)

        status, output = self.target.run("cat %s/netlabel" %self.smack_path)
        self.assertIn(
            expected_label, output, 
            "Did not find expected label in output: %s" %output)

        test_label="253.253.253.0/24 TheOther"
        status, output = self.target.run(
            "echo -n '%s' > %s/netlabel" %(test_label, self.smack_path))
        self.assertEqual(
            status, 0, 
            "Netlabel /24 could not be set. Output: %s" %output)

        status, output = self.target.run("cat %s/netlabel" %self.smack_path)
        self.assertIn(
            test_label, output, 
            "Did not find expected label in output: %s" %output)

class SmackCipso(SmackBasicTest):
    @skipUnlessPassed('test_ssh')
    def test_smack_cipso(self):
        '''Test if smack cipso rules can be set'''
        #      12345678901234567890123456789012345678901234567890123456
        ruleA="TheOneA                 2   0   "
        ruleB="TheOneB                 3   1   55  "
        ruleC="TheOneC                 4   2   17  33  "

        status, output = self.target.run(
            "echo -n '%s' > %s/cipso" %(ruleA, self.smack_path))
        self.assertEqual(status, 0, 
            "Could not set cipso label A. Ouput: %s" %output)

        status, output = self.target.run(
            "cat %s/cipso | grep '^TheOneA'" %self.smack_path)
        self.assertEqual(status, 0, "Cipso rule A was not set")
        self.assertIn(" 2", output, "Rule A was not set correctly")

        status, output = self.target.run(
            "echo -n '%s' > %s/cipso" %(ruleB, self.smack_path))
        self.assertEqual(status, 0, 
            "Could not set cipso label B. Ouput: %s" %output)

        status, output = self.target.run(
            "cat %s/cipso | grep '^TheOneB'" %self.smack_path)
        self.assertEqual(status, 0, "Cipso rule B was not set")
        self.assertIn("/55", output, "Rule B was not set correctly")

        status, output = self.target.run(
            "echo -n '%s' > %s/cipso" %(ruleC, self.smack_path))
        self.assertEqual(
            status, 0, 
            "Could not set cipso label C. Ouput: %s" %output)

        status, output = self.target.run(
            "cat %s/cipso | grep '^TheOneC'" %self.smack_path)
        self.assertEqual(status, 0, "Cipso rule C was not set")
        self.assertIn("/17,33", output, "Rule C was not set correctly")

class SmackDirect(SmackBasicTest):
    @skipUnlessPassed('test_ssh')
    def test_smack_direct(self):
        status, initial_direct = self.target.run(
            "cat %s/direct" %self.smack_path)

        test_direct="17"
        status, output = self.target.run(
            "echo '%s' > %s/direct" %(test_direct, self.smack_path))
        self.assertEqual(status, 0 , 
            "Could not set smack direct. Output: %s" %output)
        status, new_direct = self.target.run("cat %s/direct" %self.smack_path)
        # initial label before checking
        status, output = self.target.run(
            "echo '%s' > %s/direct" %(initial_direct, self.smack_path))
        self.assertEqual(
            test_direct, new_direct.strip(), 
            "Smack direct label does not match.")


class SmackAmbient(SmackBasicTest):
    @skipUnlessPassed('test_ssh')
    def test_smack_ambient(self):
        test_ambient = "test_ambient"
        initial_ambient = self.target.run("cat %s/ambient" %self.smack_path)
        status, output = self.target.run(
            "echo '%s' > %s/ambient" %(test_ambient, self.smack_path))
        self.assertEqual(status, 0, 
            "Could not set smack ambient. Output: %s" %output)

        status, output = self.target.run("cat %s/ambient" %self.smack_path)
        # Filter '\x00', which is sometimes added to the ambient label
        new_ambient = filter(lambda x: x in string.printable, output)
        status, output = self.target.run(
            "echo '%s' > %s/ambient" %(initial_ambient, self.smack_path))
        self.assertEqual(
            test_ambient, new_ambient.strip(), 
            "Ambient label does not match")


class SmackloadBinary(SmackBasicTest):
    @skipUnlessPassed('test_ssh')
    def test_smackload(self):
        '''Test if smackload command works'''
        rule="testobject testsubject rwx"

        status, output = self.target.run("echo -n '%s' > /tmp/rules" %rule)
        status, output = self.target.run("smackload /tmp/rules")
        self.assertEqual(
            status, 0, 
            "Smackload failed to load rule. Output: %s" %output)

        status, output = self.target.run(
            "cat %s/load | grep '%s'" %(self.smack_path, rule))
        self.assertEqual(status, 0, "Smackload rule was loaded correctly")

class SmackcipsoBinary(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_smackcipso(self):
        '''Test if smackcipso command works'''
        #     12345678901234567890123456789012345678901234567890123456
        rule="cipsolabel                  2   2   "

        status, output = self.target.run("echo '%s' | smackcipso" %rule)
        self.assertEqual(
            status, 0, 
            "Smackcipso failed to load rule. Output: %s" %output)

        status, output = self.target.run(
            "cat %s/cipso | grep 'cipsolabel'" %self.smack_path)
        self.assertEqual(status, 0, "Smackload rule was loaded correctly")
        self.assertIn(
            "2/2", output, 
            "Rule was not set correctly. Got: %s" %output)

class SmackEnforceFileAccess(SmackBasicTest):
    @skipUnlessPassed('test_ssh')
    def test_smack_enforce_file_access(self):
        '''Test if smack file access is enforced (rwx)

        test needs to change the running label of the current process, 
        so whole test takes places on image
        '''
        status, output = self.target.run("ls /tmp/smack_test_file_access.sh")
        if status != 0:
            self.target.copy_to(
                os.path.join(self.files_dir, 'smack_test_file_access.sh'),
                "/tmp/smack_test_file_access.sh")

        status, output = self.target.run("bash /tmp/smack_test_file_access.sh")
        self.assertEqual(status, 0, output)

class SmackEnforceMmap(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_smack_mmap_enforced(self):
        '''Test if smack mmap access is enforced'''
        raise unittest.SkipTest("Depends on mmap_test, which was removed from the layer while investigating its license.")
    
        #      12345678901234567890123456789012345678901234567890123456
        delr1="mmap_label              mmap_test_label1        -----"
        delr2="mmap_label              mmap_test_label2        -----"
        delr3="mmap_file_label         mmap_test_label1        -----"
        delr4="mmap_file_label         mmap_test_label2        -----"
        
        RuleA="mmap_label              mmap_test_label1        rw---"
        RuleB="mmap_label              mmap_test_label2        r--at"
        RuleC="mmap_file_label         mmap_test_label1        rw---"
        RuleD="mmap_file_label         mmap_test_label2        rwxat"

        mmap_label="mmap_label"
        file_label="mmap_file_label"
        test_file = "/tmp/smack_test_mmap"
        self.target.copy_to(os.path.join(get_files_dir(), "mmap_test"), "/usr/bin/")
        mmap_exe = "/usr/bin/mmap_test"
        status, echo = self.target.run("which echo")
        status, output = self.target.run("ls /tmp/notroot.py")
        if status != 0:
            self.target.copy_to(
                os.path.join(self.files_dir, 'notroot.py'),
                "/tmp/notroot.py")
        status, output = self.target.run(
            "python /tmp/notroot.py %d %s %s 'test' > %s" %(self.uid, self.current_label, echo, test_file))
        status, output = self.target.run("ls %s" %test_file)
        self.assertEqual(status, 0, "Could not create mmap test file")
        self.target.run("chsmack -m %s %s" %(file_label, test_file))
        self.target.run("chsmack -e %s %s" %(mmap_label, mmap_exe))

        # test with no rules with mmap label or exec label as subject
        # access should be granted
        self.target.run('echo -n "%s" > %s/load' %(delr1, self.smack_path))
        self.target.run('echo -n "%s" > %s/load' %(delr2, self.smack_path))
        self.target.run('echo -n "%s" > %s/load' %(delr3, self.smack_path))
        self.target.run('echo -n "%s" > %s/load' %(delr4, self.smack_path))
        status, output = self.target.run("mmap_test %s 0 2" % test_file)
        self.assertEqual(
            status, 0, 
            "Should have mmap access without rules. Output: %s" %output)
        
        # add rules that do not match access required
        self.target.run('echo -n "%s" > %s/load' %(RuleA, self.smack_path))
        self.target.run('echo -n "%s" > %s/load' %(RuleB, self.smack_path))
        status, output = self.target.run("mmap_test %s 0 2" % test_file)
        self.assertNotEqual(
            status, 0, 
            "Should not have mmap access with unmatching rules. " + 
            "Output: %s" %output)
        self.assertIn(
            "Permission denied", output, 
            "Mmap access should be denied with unmatching rules")
        
        # add rule to match only partially (one way)
        self.target.run('echo -n "%s" > %s/load' %(RuleC, self.smack_path))
        status, output = self.target.run("mmap_test %s 0 2" %test_file)
        self.assertNotEqual(
            status, 0,
            "Should not have mmap access with partial matching rules. " + 
            "Output: %s" %output)
        self.assertIn(
            "Permission denied", output,
            "Mmap access should be denied with partial matching rules")
       
        # add rule to match fully
        self.target.run('echo -n "%s" > %s/load' %(RuleD, self.smack_path))
        status, output = self.target.run("mmap_test %s 0 2" %test_file)
        self.assertEqual(
            status, 0, 
            "Should have mmap access with full matching rules." +
            "Output: %s" %output)

class SmackEnforceTransmutable(SmackBasicTest):   

    def test_smack_transmute_dir(self):
        '''Test if smack transmute attribute works

        test needs to change the running label of the current process, 
        so whole test takes places on image
        '''
        test_dir = "/tmp/smack_transmute_dir"
        label="transmute_label"
        status, initial_label = self.target.run("cat /proc/self/attr/current")

        self.target.run("mkdir -p %s" %test_dir)
        self.target.run("chsmack -a %s %s" %(label, test_dir))
        self.target.run("chsmack -t %s" %test_dir)
        self.target.run(
            "echo -n '%s %s rwxat' | smackload" %(initial_label, label) )

        self.target.run("touch %s/test" %test_dir)
        status, output = self.target.run("chsmack %s/test" %test_dir)
        self.assertIn(
            'access="%s"' %label, output,
            "Did not get expected label. Output: %s" %output)
        

class SmackTcpSockets(SmackBasicTest):
    def test_smack_tcp_sockets(self):
        '''Test if smack is enforced on tcp sockets

        whole test takes places on image, depends on tcp_server/tcp_client'''
       
        self.target.copy_to(os.path.join(get_files_dir(), "tcp_client"), "/usr/bin/")
        self.target.copy_to(os.path.join(get_files_dir(), "tcp_server"), "/usr/bin/")
        status, output = self.target.run("ls /tmp/test_smack_tcp_sockets.sh")
        if status != 0:
            self.target.copy_to(
                os.path.join(self.files_dir, 'test_smack_tcp_sockets.sh'),
                "/tmp/test_smack_tcp_sockets.sh")

        status, output = self.target.run("bash /tmp/test_smack_tcp_sockets.sh")
        self.assertEqual(status, 0, output)

class SmackUdpSockets(SmackBasicTest):
    def test_smack_udp_sockets(self):
        '''Test if smack is enforced on udp sockets

        whole test takes places on image, depends on udp_server/udp_client'''

        self.target.copy_to(os.path.join(get_files_dir(), "udp_client"), "/usr/bin/")
        self.target.copy_to(os.path.join(get_files_dir(), "udp_server"), "/usr/bin/")
        status, output = self.target.run("ls /tmp/test_smack_udp_sockets.sh")
        if status != 0:
            self.target.copy_to(
                os.path.join(self.files_dir, 'test_smack_udp_sockets.sh'),
                "/tmp/test_smack_udp_sockets.sh")

        status, output = self.target.run("bash /tmp/test_smack_udp_sockets.sh")
        self.assertEqual(status, 0, output)

class SmackFileLabels(SmackBasicTest):

    @skipUnlessPassed('test_ssh')
    def test_smack_labels(self):
        '''Check for correct Smack labels.'''
        expected = '''
/tmp access="*"
/etc access="System::Shared" transmute="TRUE"
/etc/skel access="User::Home"
/var/log access="System::Log" transmute="TRUE"
/var/tmp access="*"
'''
        (status, output) = self.target.run(
            'chsmack -L ' + 
            ' '.join([x.split()[0] for x in expected.split('\n') if x]))
        self.assertEqual(
            status, 0, msg="status and output: %s and %s" %(status,output))
        self.assertEqual(output.strip(), expected.strip())



