from libmeross.commands import device, cloud, chip

from .shared import submodule

CMD_LIST = (submodule(device), submodule(cloud), submodule(chip))
