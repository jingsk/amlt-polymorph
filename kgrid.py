


def get_kpts_from_kpd(atoms, kpd, only_even = False, show_kpts = True ):
    import numpy as np
    #kpd = kpoint_density
    
    if only_even:
        step = 2
    else:
        step = 1
    
    rcell = atoms.get_reciprocal_cell()
    rlengths = [np.linalg.norm(rcell[i]) for i in range(3)]
    lengths = atoms.get_cell_lengths_and_angles()[0:3]
    
    vol = atoms.get_volume()
    min_kpts = kpd/vol # BZ volume = 1/cell volume (without 2pi factors)
    
    if False:
        linear_density = (min_kpts  /( rlengths[0] * rlengths[1] * rlengths[2])) ** (1 / 3)
    else:
        mult = (min_kpts  * lengths[0] * lengths[1] * lengths[2]) ** (1 / 3)

        nkpt_frac  = np.zeros(3)
        for i, l in enumerate(lengths):
            nkpt_frac[i] = max(mult / l, step)
        
    nkpt       = np.floor(nkpt_frac/step)*step
    delta_ceil = np.ceil(nkpt_frac/step) *step - nkpt_frac # measure of which axes are closer to a whole number

    actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]

    check_order = np.argsort(delta_ceil) # we do this so we keep the grid as even as possible only rounding up when they are close


    i = 0 # tracks which index we checked
    if actual_kpd < kpd:
        if np.isclose(nkpt_frac[check_order[0]], nkpt_frac[check_order[1]]) and \
            np.isclose(nkpt_frac[check_order[1]], nkpt_frac[check_order[2]]):
                nkpt[check_order[0]] = nkpt[check_order[0]] +step
                nkpt[check_order[1]] = nkpt[check_order[1]] +step
                nkpt[check_order[2]] = nkpt[check_order[2]] +step
                actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]
                i = 3

        elif np.isclose(nkpt_frac[check_order[0]], nkpt_frac[check_order[1]]):
            nkpt[check_order[0]] = nkpt[check_order[0]] +step
            nkpt[check_order[1]] = nkpt[check_order[1]] +step
            actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]
            i = 2

        elif np.isclose(nkpt_frac[check_order[1]], nkpt_frac[check_order[2]]):
            nkpt[check_order[0]] = nkpt[check_order[0]] +step
            actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]
            if actual_kpd < kpd:
                nkpt[check_order[1]] = nkpt[check_order[1]] +step
                nkpt[check_order[2]] = nkpt[check_order[2]] +step
                actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]
            i = 3

    while actual_kpd < kpd and i<=2:
        nkpt[check_order[i]] = nkpt[check_order[i]] +step
        actual_kpd = vol * nkpt[0]*nkpt[1]*nkpt[2]
        i+=1

    kpts = [int(nkpt[i]) for i in range(3)]
    
    if show_kpts:
        print('kgrid: %i x %i x %i'%tuple(kpts))
        print('kpd target: %.3f, actual kpd: %.3f'%(kpd, actual_kpd))
        for i in range(3):
            print('kvec%i density: %.3f' %(i,kpts[i]/rlengths[i]))
    return kpts






def safe_kgrid_from_cell_volume(atoms, kpoint_density):
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
