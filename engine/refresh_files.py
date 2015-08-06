import os
import sys

usage = '<from directory> <to directory>'

if len(sys.argv) < 3:
    print 'Usage: python ' + sys.argv[0] + ' ' + usage
    sys.exit(1)

from_directory = sys.argv[1]
to_directory = sys.argv[2]

for file_name in os.listdir(from_directory):
    print file_name
    from_file_time = os.path.getmtime(from_directory + '/' + file_name)
    if os.path.isfile(to_directory + '/' + file_name):
        to_file_time = os.path.getmtime(to_directory + '/' + file_name)
        if from_file_time > to_file_time:
            print 'Seems like you have newer version for file ' + file_name + '.'
            answer = raw_input('Should I copy it? [y/n] ')
            if answer.lower() in ['y', 'yes']:
                pass
    
