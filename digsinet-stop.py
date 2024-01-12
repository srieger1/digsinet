#!/usr/bin/env python3
import os
import yaml
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', help='Config file', default='./digsinet.yml')
    args = parser.parse_args()

    with open(args.config, 'r') as stream:
        config = yaml.safe_load(stream)

        os.system(f"clab destroy -t {config['topology']['file']}")

        for sibling in config['siblings']:
            sibling_config = config['siblings'].get(sibling)
            if sibling_config:
                if sibling_config.get('autostart'):
                    os.system(f"clab destroy -t {config['name']}_sib_{sibling}.clab.yml")

        # clab_topology_definition['topology']['nodes'].append(sibling)

if __name__ == '__main__':
    main()
