import sys
from time import time
from datetime import datetime
import numpy as np
import pandas as pd
import argparse
from tqdm import tqdm
from helicalc import helicalc_dir, helicalc_data
from helicalc.auxiliary_integrators import RadialStraightIntegrator1D
from helicalc.tools import generate_cartesian_grid_df, generate_cylindrical_grid_df
from helicalc.constants import dr_radial_dict, TSd_grid, DS_grid, DS_FMS_cyl_grid, DS_FMS_cyl_grid_SP
from helicalc.solenoid_geom_funcs import load_all_geoms

# data
datadir = helicalc_data+'Bmaps/helicalc_partial/'

# load straight bus bars, dump all other geometries
df_dict = load_all_geoms(version=13, return_dict=True)
df_radial_coils = df_dict['radial_coils']

# assume same chunk size for everything, for now
# N_per_chunk = 10000 # original, from busbars
N_per_chunk = 8000

regions = {'TSd': TSd_grid, 'DS': DS_grid, 'DSCylFMS': DS_FMS_cyl_grid,
           'DSCylFMSAll': [DS_FMS_cyl_grid, DS_FMS_cyl_grid_SP]}

if __name__=='__main__':
    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--Region',
                        help='Which region of Mu2e to calculate? '+
                        '["DS"(default), "TSd", "DSCylFMS", "DSCylFMSAll"]')
    parser.add_argument('-C', '--Coil',
                        help='Coil number [56(default), 57, 58, ... , 66]. '+
                        'This is supported only for DS coils.')
    parser.add_argument('-D', '--Device',
                        help='Which GPU to use? [0 (default), 1, 2, 3].')
    parser.add_argument('-t', '--Testing',
                        help='Calculate using small subset of field points '+
                        ' (N=100000)? "y"/"n"(default).')
    args = parser.parse_args()
    # fill defaults where needed
    if args.Region is None:
        args.Region = 'DS'
    else:
        args.Region = args.Region.strip()
    reg = args.Region
    if args.Coil is None:
        args.Coil = "56"
    else:
        args.Coil = args.Coil.strip()
    df_conds = df_radial_coils[np.isin(df_radial_coils, [f'{args.Coil}in', f'{args.Coil}out'])]
    # pick correct integration grid based on ???
    ind_dr = 1
    dr_ = dr_radial_dict[ind_dr]
    if args.Device is None:
        args.Device = 0
    else:
        args.Device = int(args.Device.strip())
    if args.Testing is None:
        args.Testing = False
    else:
        args.Testing = args.Testing.strip() == 'y'
    # set up base directory/name
    if args.Testing:
        base_name = f'Bmaps/auxiliary_partial/tests/Mau13.{reg}_region.'+\
                     'test-radial_coil.'
    else:
        base_name = f'Bmaps/auxiliary_partial/Mau13.{reg}_region.'+\
                     'standard-radial_coil.'
    # print configs
    print(f'Region: {reg}')
    # redirect stdout to log file
    dt = datetime.strftime(datetime.now(), '%Y-%m-%d_%H%M%S')
    log_file = open(datadir+f"logs/{dt}_calculate_{reg}_"+
                    "region_radial_coil.log", "w")
    old_stdout = sys.stdout
    sys.stdout = log_file
    # find correct chunk size
    N_calc = N_per_chunk
    # create grid
    if reg in ['DSCylFMS', 'DSCylFMSAll']:
        df = generate_cylindrical_grid_df(regions[reg], dec_round=9)
    else:
        df = generate_cartesian_grid_df(regions[reg])
    if args.Testing:
        df = df.iloc[:100000].copy()
    # initialize conductor
    for i in range(len(df_conds)):
        df_cond = df_conds.iloc[i]
        myRadial = RadialStraightIntegrator1D(df_cond, dr=dr_, dev=args.Device)
        # integrate!
        df = myRadial.integrate_grid(df, N_batch=N_calc, tqdm=tqdm)
    # save!
    myRadial.save_grid_calc(savetype='pkl', savename=base_name+
                            f'Coil_Num_{args.Coil}_radial',
                            all_cols=True)