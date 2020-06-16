"""Commands for generating DFT input files. Not intended to be called from
places besides control_script.py."""
import numpy as np
import os
from amlt import reasonable_random_structure_maker, PolymorphD3, try_mkdir
from ase import io
from os.path import isfile



def vasp_job_maker(name_prefix,
                   jobs,
                   job_command,
                   job_script_name,
                   job_script_template,
                   md_temperature_range=(100, 600),
                   submit = False,
                   random_structure_parameters = None,
                   known_structures=[],
                   polymorphD3_parameters = None,
                   first_structure = 'POSCAR.initial',
                   magmom_filename = 'MAGMOMS.initial'):
    """Creates VASP input files and controls job submission.
    Args:
        name_prefix (String):
        jobs (Iterable of Lists): Lists contain
            [0]: the number of structures as an integer,
            [1]: the type of structural modification as a string,
                options are "known" which does not change the known crystalline
                polymorphs, "polymorphD3" which adds vacancies and atomic
                displacements to the known crystalline polymorphs, and "random"
                which creates totally random arrangements of atoms.
            [2]: which ase calculator template to use as a string,
                options are "sp", "md", or "relax". sp means single point
        job_command (String): command used to submit jobs to scheduler
        job_script_name (String): path to write the job script
        job_script_template (String): Text of job submission script with string
            formatting for calling the right calculator script.
        md_temperature_range (Tuple of numbers): Min and max MD temperature
        submit (Boolean): Send jobs to SLURM scheduler if True
        random_structure_parameters (Dict): Control parameters for making
            random structures.  See rrsm.py for details
        known_structures (List): List of CIF filepaths for known polymorphs
        polymorphD3_parameters (Dict): Control parameters for creating
            distorted structures with vacancies and displacements.
            See polymorphD3.py for more details
        first_structure (String): Saved filename of starting structure
        magmom_filename (String): Saved filename of starting magnetic moments
    """


    twd = os.getcwd()

    for job_type in jobs:

        job_type_dir = job_type[1] +'_' + job_type[2] +'/'

        try_mkdir(job_type_dir)

        if job_type[1] =='known':
            n_structures = len(known_structures)
        else:
            n_structures = job_type[0]

        for structure_number in range(n_structures):

            struct_dir =job_type_dir + str(structure_number) +'/'
            try_mkdir(struct_dir)

            # If input structure files have not been generated, we need to
            # write a POSCAR and MAGMOM file based on the job type
            if not isfile(struct_dir+ first_structure):


                if job_type[1] == 'random':
                    atoms = reasonable_random_structure_maker(**random_structure_parameters)
                    #if callable(random_structure_parameters['magmom_generator']):

                elif job_type[1] == 'polymorphD3':
                    index = np.random.random_integers(0, len(known_structures)-1)
                    atoms = PolymorphD3(known_structures[index], **polymorphD3_parameters).atoms_out

                elif job_type[1] =='known':
                    atoms = known_structures[structure_number]
                else:
                    raise Exception('Structure type "{}" not recognized'.format(job_type[1]))

                io.write(struct_dir+ first_structure, atoms, format = 'vasp')
                magmoms = atoms.get_initial_magnetic_moments()
                # magmom check
                if np.sqrt(magmoms.dot(magmoms)) > 0.0000001:
                    np.savetxt(struct_dir + magmom_filename,  magmoms.T)

                if job_type[2] == 'md':
                    temp = np.random.rand()*(max(md_temperature_range) - min(md_temperature_range)) + min(md_temperature_range)
                    np.savetxt(struct_dir+'temperature.txt', [temp,temp])

                print(struct_dir, 'structure created')


            # If VASP has not been run yet, we then create the job script for
            # the SLURM job scheduler.
            if not isfile(struct_dir+'OUTCAR'):

                fid = open(struct_dir+ job_script_name,'w')
                job_name = "{}_{}_{}_{}".format(
                        name_prefix,
                        job_type[1],
                        job_type[2],
                        structure_number)
                fid.write(job_script_template.format(job_name, job_type[2]))
                fid.close()


                if submit:
                    os.chdir(struct_dir)
                    os.system(job_command+' '+job_script_name)
                    os.chdir(twd)
                    print(struct_dir, 'job submitted')
                else:
                    print(struct_dir, 'job not yet run')
            # If VASP has already been run, we can write the resulting ionic
            # steps to ase trajectory files.
            else:
                if isfile(struct_dir + 'images.traj'):
                    size = os.path.getsize(struct_dir + 'images.traj')
                    print(size)
                    if size > 4:
                        images = io.trajectory.Trajectory( struct_dir + 'images.traj', mode = 'r')
                    else:
                        images = []
                else:
                    images = io.read(struct_dir+'OUTCAR', index = ':')
                    my_traj = io.trajectory.Trajectory( struct_dir + 'images.traj', mode = 'w')

                    for atoms in images:
                        my_traj.write(atoms = atoms)
                    my_traj.close()
                
                print(struct_dir.ljust(25), 'has {} images'.format(len(images)))




def safe_kgrid_from_cell_volume(atoms, kpoint_density ):
    import numpy as np
    kpd = kpoint_density
    lengths_angles = atoms.get_cell_lengths_and_angles()
    vol = atoms.get_volume()
    lengths = lengths_angles[0:3]
    ngrid = kpd/vol # BZ volume = 1/cell volume (without 2pi factors)
    mult = (ngrid * lengths[0] * lengths[1] * lengths[2]) ** (1 / 3)

    nkpt_frac  = np.zeros(3)
    for i, l in enumerate(lengths):
        nkpt_frac[i] = max(mult / l, 1)

    nkpt       = np.floor(nkpt_frac)
    delta_ceil = np.ceil(nkpt_frac)-nkpt_frac # measure of which axes are closer to a whole number

    actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]

    check_order = np.argsort(delta_ceil) # we do this so we keep the grid as even as possible only rounding up when they are close


    i = 0
    if actual_kpd < kpd:
        if np.isclose(nkpt_frac[check_order[0]], nkpt_frac[check_order[1]]) and np.isclose(nkpt_frac[check_order[1]], nkpt_frac[check_order[2]]):
            nkpt[check_order[0]] = nkpt[check_order[0]] +1
            nkpt[check_order[1]] = nkpt[check_order[1]] +1
            nkpt[check_order[2]] = nkpt[check_order[2]] +1
            actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]
            i = 3

        elif np.isclose(nkpt_frac[check_order[0]], nkpt_frac[check_order[1]]):
            nkpt[check_order[0]] = nkpt[check_order[0]] +1
            nkpt[check_order[1]] = nkpt[check_order[1]] +1
            actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]
            i = 2

        elif np.isclose(nkpt_frac[check_order[1]], nkpt_frac[check_order[2]]):
            nkpt[check_order[0]] = nkpt[check_order[0]] +1
            actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]
            if actual_kpd < kpd:
                nkpt[check_order[1]] = nkpt[check_order[1]] +1
                nkpt[check_order[2]] = nkpt[check_order[2]] +1
                actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]
            i = 3

    while actual_kpd < kpd and i<=2:
        nkpt[check_order[i]] = nkpt[check_order[i]] +1
        actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]
        i+=1

    kp_as_ints = [int(nkpt[i]) for i in range(3)]
    return kp_as_ints


def kgrid_from_cell_volume(atoms, kpoint_density ):
    import math
    kpd = kpoint_density
    lengths_angles = atoms.get_cell_lengths_and_angles()
    #if math.fabs((math.floor(kppa ** (1 / 3) + 0.5)) ** 3 - kppa) < 1:
    #    kppa += kppa * 0.01
    lengths = lengths_angles[0:3]
    ngrid = kpd/atoms.get_volume() # BZ volume = 1/cell volume (withot 2pi factors)
    mult = (ngrid * lengths[0] * lengths[1] * lengths[2]) ** (1 / 3)

    num_divf = [int(math.floor(max(mult / l, 1))) for l in lengths]
    kpdf = atoms.get_volume()*num_divf[0]*num_divf[1]*num_divf[2]
    errorf = abs(kpd - kpdf)/kpdf # not a type being 0.5 is much worse than being 1.5


    num_divc = [int(math.ceil(mult / l)) for l in lengths]
    kpdc = atoms.get_volume()*num_divc[0]*num_divc[1]*num_divc[2]
    errorc = abs(kpd - kpdc)/kpdc #same

    if errorc < errorf :
        num_div = num_divc
    else:
        num_div = num_divf

    #num_div = num_divf
    return num_div
