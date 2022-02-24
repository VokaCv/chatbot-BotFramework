from pathlib import Path
import os


def find_me(pckg_name, starting_point):
    found_in = starting_point

    while not pckg_name in os.listdir(found_in):
        found_in_before = found_in
        found_in = Path(found_in).parent

        if found_in_before == found_in:
            return None
            

    return found_in


if __name__ == '__main__':
    package_to_find = 'p10_00_helper_func'
    start_at = Path(os.path.abspath(__file__)).parent
    found_parent = find_me(package_to_find, starting_point=start_at)
    print('FOUND IN', found_parent)



