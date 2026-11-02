from testrunner import create_overlay
from testrunner import start_vm
import os

def test_overlay():
    create_overlay("/home/davidx/Personal_Projects/KVMProject/images/noble-server-cloudimg-amd64.img", "overlays/run1.qcow2")

def test_start_vm():
    vm_process = start_vm("overlays/run1.qcow2", "seed/seed.iso", "2222")
    vm_process.terminate()
    vm_process.wait()