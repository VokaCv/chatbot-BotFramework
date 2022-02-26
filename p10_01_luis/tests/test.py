# -*- coding: utf-8 -*-
# +
import sys, os
import warnings
import unittest
from pathlib import Path


# Add parent paskage to sys.path so it can be imported (in child folder)
def find_pckg(pckg_name, starting_point=""):  
    if starting_point == "":
        starting_point =  str(Path(os.path.realpath(__file__)).parent)       
    
    found_in = starting_point

    while not pckg_name in os.listdir(found_in):
        found_in_before = found_in
        found_in = Path(found_in).parent

        if found_in_before == found_in:
            return None

    if found_in not in sys.path:
        sys.path.append(str(found_in))        
    return str(found_in)

# name of the package to add
path = find_pckg("p10_01_luis")
from p10_01_luis.utils import get_prediction_luis, LuisEnv

warnings.filterwarnings("ignore", category=DeprecationWarning)


class TestLuis(unittest.TestCase):

    def test_detect_none_intent(self):
        pred = get_prediction_luis(
            LuisEnv(),
            "Hello Bot! What time is it?"
        )
        
        self.assertEqual(pred["prediction"]["topIntent"], "None")
    
    def test_detect_ReserverVoyage_intent(self):
        pred = get_prediction_luis(
            LuisEnv(),
            "I want to go to Paris from Marseille on 22/2/2022"
        )
        
        self.assertEqual(pred["prediction"]["topIntent"], "ReserverVoyage")

if __name__ == '__main__':
    unittest.main()
