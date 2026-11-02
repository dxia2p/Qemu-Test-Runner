import subprocess
import time
import os

def create_overlay(base, path, sizeGB=10):
    # Create the overlay with qemu-img create
    result = subprocess.run(["qemu-img", "create", "-f", "qcow2", "-b", base, "-F", "qcow2", path, str(sizeGB) + "G"], capture_output=True, text=True, check=True)

def start_vm(overlay, seed, ssh_port):
    # -nic user,hostfwd=tcp::<ssh_port>-:22 forwards tcp traffic from port 2222 on the host to port 22 9ssh) inside the vm
    process = subprocess.Popen(["qemu-system-x86_64", "-enable-kvm", "-m", "2G", "-smp", "2", "-drive",
                                f"file={overlay},if=virtio", "-drive", f"file={seed},format=raw,if=virtio",
                                "-nic", f"user,hostfwd=tcp::{ssh_port}-:22", "-display", "none", "-serial", "file:vm-serial.log", "-monitor", "none"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    return process

def ssh_run(port, hostname, command, opts, timeout=60):

    result = subprocess.run(
        ["ssh", "-p", str(port), *opts, hostname, command], capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr

def scp_to(port, local, hostname, remote, opts):
    subprocess.run(
        ["scp", "-P", str(port), *opts, local, f"{hostname}:{remote}"], check=True
    )

def wait_for_ssh(port, hostname, opts, timeout=120):
    # Wait for ssh to be ready
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            code, _, _ = ssh_run(port, hostname, "true", opts)
            if code == 0:
                return
        except subprocess.TimeoutExpired:
            pass
        time.sleep(2)
    raise TimeoutError(f"SSH on port {port}")

def wait_for_vm_ready(port, hostname, ssh_opts, timeout=180):
    wait_for_ssh(port, hostname, ssh_opts, timeout)
    code, out, err = ssh_run(port, hostname, "cloud-init status --wait", ssh_opts, timeout=timeout)
    if code != 0:
        raise RuntimeError(f"cloud-init did not finish cleanly: {out} {err}")

def run_test(port, script_path, hostname, ssh_opts):
    scp_to(port, script_path, hostname, "~/", ssh_opts)

    script_name = os.path.basename(script_path)
    code, stdout, stderr = ssh_run(port, hostname, f"~/{script_name}", ssh_opts)
    if code != 0:
        raise RuntimeError(f"Error running script inside vm: {stdout} {stderr}")
    
    return code, stdout, stderr
    
def stop_vm(proc):
    proc.terminate()
    proc.wait()

def main():
    try:
        overlay_path = "overlays/run1.qcow2"
        base_path = "/home/davidx/Personal_Projects/KVMProject/images/noble-server-cloudimg-amd64.img"
        seed_path = "seed/seed.iso"
        ssh_port = 2222
        name = "tester@localhost"

        vm_process = None

        print("Creating overlay at " + overlay_path + "...")
        create_overlay(base_path, overlay_path)

        print("Starting qemu-system-x86_64...")
        vm_process = start_vm(overlay_path, seed_path, ssh_port)

        SSH_OPTS = [
            "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",   # never prompt for a password
        ]

        print("Waiting for ssh...")
        wait_for_vm_ready(ssh_port, name, SSH_OPTS)

        print("Uploading testcase and running test...")
        code, stdout, stderr = run_test(ssh_port, "tests/testscript.sh", name, SSH_OPTS)

        print("-----")
        print(f"Test exited with code {code}")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        print("-----")


    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if vm_process:
            print("\nPowering off VM...")
            stop_vm(vm_process)

if __name__ == "__main__":
    main()
