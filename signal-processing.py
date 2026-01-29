import os
import subprocess
import matplotlib.pyplot as plt

def read_csr(chip):
    output = os.popen(f"{chip}.exe cfg --address 0x0").read().strip()
    return int(output, 16)

def write_csr(chip, value):
    print(f"csr register content from {chip}: ")
    os.system(f"{chip}.exe cfg --address 0x0 --data {hex(value)}")

def drive_signal(unit, value, count=1, silent=True):
    for _ in range(count):
        if silent:
            subprocess.run(
                f"impl{unit} sig --data {hex(value)}",
                shell=True,
                stdout=subprocess.DEVNULL,
            )
        else:
            os.system(f"impl{unit}.exe sig --data {hex(value)}")

#similar to drive_signal func but show the output instead of silencing it 
def drive_and_capture(chip, value):
    output = os.popen(f"{chip}.exe sig --data {hex(value)}").read().strip()
    return int(output, 16)

def read_cfg_file(filename):
    coeffs = []
    with open(filename, "r") as f:
        next(f)  # skip header
        for line in f:
            coef, en, value = line.strip().split(",")
            coeffs.append({
                "coef": int(coef),
                "en": int(en),
                "value": int(value, 16)
            })
    return coeffs

def read_coef(chip):
    output = os.popen(f"{chip}.exe cfg --address 0x4").read().strip()
    return int(output, 16)

def write_coef(chip, value, coef_idx):
    shift = coef_idx * 8
    coef_reg = read_coef(chip)
    coef_reg &= ~(0xFF << shift)
    coef_reg |= (value & 0xFF) << shift
    os.system(f"{chip}.exe cfg --address 0x4 --data {hex(coef_reg)}")


def program_coefficients(coeff_config, chip):
    csr = read_csr(chip)  # ALWAYS read CSR first

    coef_idx = coeff_config["coef"]
    
    print(f"Writing to coef for {chip} with the config file {coeff_config}")

    if coeff_config["en"] == 1:
        csr |= (1 << (coef_idx + 1))     # enable coefficient, plus 1 because coef position start at index = 1 not 0
        write_csr(chip, csr)
        write_coef(chip,coeff_config["value"], coef_idx)
    else:
        csr &= ~(1 << (coef_idx + 1))    # disable coefficient
        write_csr(chip, csr)

def read_vec_file(filename):
    values = []
    with open(filename, "r") as f:
        for line in f:
            values.append(int(line.strip(), 16))
    return values

config_file = [0,4,7,9]
arr_size = len(config_file)
chips = ["impl0"]

for i in range(len(config_file)):

    # 1. reset + enable BOTH chips
    for chip in chips:
        os.system(f"{chip}.exe com --action reset")
        os.system(f"{chip}.exe com --action enable")

        csr = read_csr(chip)
        csr |= (1 << 5)   # HALT
        csr |= (1 << 17)  # IBCLR: clear input buffer
        csr |= (1 << 18)  # TCLR: clear filter taps
        write_csr(chip, csr)

    # 2. program coefficients to BOTH
    coeffs_config = read_cfg_file(f"p{config_file[i]}.cfg")

    for cfg in coeffs_config:
        print(f"Reading config file: pk{config_file[i]}")
        for chip in chips:
            print(f"configuring coefficient for {chip}")
            program_coefficients(cfg, chip)

    # 3. release halt + enable filter
    for chip in chips:
        csr = read_csr(chip)
        csr &= ~(1 << 5)     # HALT = 0
        csr |= 1             # FEN = 1
        write_csr(chip, csr)

    # 4. drive vector + capture outputs
    vec_file = read_vec_file("sqr.vec")

    dut_out = []
    # golden_out = []

    for v in vec_file:
        dut_out.append(drive_and_capture("impl0", v))
        # golden_out.append(drive_and_capture("golden", v))

    # 5. plot
    plt.figure(figsize=(10, 5))
    #plt.plot(vec_file, label="Input", drawstyle="steps-post")
    plt.plot(dut_out, label="DUT Output", drawstyle="steps-post")
    # plt.plot(golden_out, label="Golden Output", drawstyle="steps-post", alpha=0.7)
    plt.title(f"FIR Filter Output Comparison (p{config_file[i]}.cfg)")
    plt.xlabel("Sample Index")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.grid(True)
    plt.show()