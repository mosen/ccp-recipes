#!/usr/bin/python
#
# Copyright 2016 Mosen
#                Tim Sutton
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# for debugging
from pprint import pprint

from autopkglib import Processor, ProcessorError

__all__ = ["CreativeCloudBuildParser"]

class CreativeCloudBuildParser:
    """This processor parses the output of the CCP build process and merges in pkginfo keys that are relevant for the
    current product."""
    description = __doc__
    input_variables = {
        "ccp_path": {
            "required": True,
            "description": "The .ccp file produced by Creative Cloud Packager",
        }
    }



    def main(self):
        pass


if __name__ == "__main__":
    processor = CreativeCloudBuildParser()
    processor.execute_shell()
