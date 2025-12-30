from libmeross.commands import device, cloud, chip, discover

from .shared import submodule

CMD_LIST = (submodule(device), submodule(cloud), submodule(chip), discover.install_parser)
