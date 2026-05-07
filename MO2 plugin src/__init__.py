import os
import site
from typing import List

site.addsitedir(os.path.join(os.path.dirname(__file__), "lib"))

from mobase import IPlugin
from .mws_handler import mws_protocol_register

def createPlugins() -> List["IPlugin"]:
    return [mws_protocol_register()]