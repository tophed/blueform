import os
from shutil import unpack_archive
from sys import argv

TARGET = argv[1]

for root, _, files in os.walk(f"bin/{TARGET}/providers/registry.terraform.io", topdown=False):
    for name in files:
        if name.endswith('.zip'):
            filename = os.path.join(root, name)
            # registry.terraform.io/hashicorp/aviatrix/terraform-provider-aviatrix_3.1.1_darwin_arm64.zip
            version = name.split('_')[1]
            print(version, filename)
            # HOSTNAME/NAMESPACE/TYPE/VERSION/TARGET
            unpack_archive(filename, extract_dir=os.path.join(root, version, TARGET))

