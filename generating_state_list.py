
fout = open('states_table.txt', 'w')
name_path = 'states_info.csv'
for line in open(name_path):
            n, m, _ = line.strip('\n').split(',')
            fout.write('<option value="{}">{}</option>\n'.format(m, n))

fout.close()