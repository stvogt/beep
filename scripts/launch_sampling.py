import sys, time
import qcfractal.interface as ptl
from pathlib import Path
from beep.converge_sampling import sampling

from optparse import OptionParser

usage = """python %prog [options]

A command line interface to sample the surface of a set of water clusters (stored in a 
QCFractal DataSet) with a small molecule or atom. This CLI is part
of the Binding Energy Evaluation Platform (BEEP).
"""
parser = OptionParser(usage=usage)
parser.add_option(
    "--client_address",
    dest="client_address",
    help="The URL address and port of the QCFractal server (default: localhost:7777)",
    default="localhost:7777",
)
parser.add_option(
    "--username",
    dest="usern",
    help="The username for the database client (Default = None)",
    default=None,
)
parser.add_option(
    "--password",
    dest="passwd",
    help="The password for the database client (Default = None)",
    default=None,
)
parser.add_option(
    "--molecule",
    dest="molecule",
    help="The name of the molecule to be sampled (from a QCFractal OptimizationDataSet collection)",
)
parser.add_option(
    "--surface_model_collection",
    dest="surface_model_collection",
    help="The name of the collection with the set of water clusters (dafault: Water_22)",
    default="Water_22",
)
parser.add_option(
    "--small_molecule_collection",
    dest="small_molecule_collection",
    help="The name of the collection containing molecules or radicals (dafault: Small_molecules)",
    default="Small_molecules",
)
parser.add_option(
    "--sampling_shell",
    dest="sampling_shell",
    type="float",
    default=2.0,
    help="The shell size of sampling space in Angstrom (Default = 2.0) ",
)
parser.add_option(
    "--sampling_condition",
    dest="sampling_condition",
    type="string",
    default='normal',
    help="How tight the sampling should be done for each surface. Options: sparse, normal, fine (Default: normal)",
)
parser.add_option(
    "-l",
    "--level_of_theory",
    dest="level_of_theory",
    help="The level of theory in the format: method_basis (default: blyp_def2-svp)",
    default="blyp_def2-svp",
)
parser.add_option(
    "--refinement_level_of_theory",
    dest="r_level_of_theory",
    help="The level of theory for geometry refinement in the format: method_basis (default: hf3c_minix)",
    default="hf3c_minix",
)
parser.add_option(
    "--rmsd_value",
    dest="rmsd_val",
    type="float",
    default=0.40,
    help="Rmsd geometrical criteria, all structure below this value will not be considered as unique. (default: 0.40 angstrom)",
)
parser.add_option(
    "--rmsd_symmetry",
    action="store_true",
    dest="rmsd_symmetry",
    help="Consider the molecular symmetry for the rmsd calculation",
)
parser.add_option(
    "-p",
    "--program",
    dest="program",
    default="psi4",
    help="The program to use for this calculation (default: psi4)",
)
parser.add_option(
    "--sampling_tag",
    dest="tag",
    default="sampling",
    help="The tag to used to specify the qcfractal-manager for the sampling optimization  (default: sampling)",
)

parser.add_option(
    "-k",
    "--keyword_id",
    dest="keyword_id",
    help="ID of the QC keywords for the OptimizationDataSet specification (default: None)",
    default=None,
)


def print_out(string, o_file):
    with open(o_file, "a") as f:
        f.write(string)


options = parser.parse_args()[0]

username = options.usern
password = options.passwd
method = options.level_of_theory.split("_")[0]
basis = options.level_of_theory.split("_")[1]
program = options.program
tag = options.tag
opt_lot = options.level_of_theory
r_lot = options.r_level_of_theory
kw_id = options.keyword_id
sampling_shell = options.sampling_shell
sampling_condition = options.sampling_condition
rmsd_symm = options.rmsd_symmetry
cluster_collection = options.surface_model_collection
mol_collection = options.small_molecule_collection
smol_name = options.molecule
rmsd_val = options.rmsd_val

client = ptl.FractalClient(
    address=options.client_address, verify=False, username=username, password=password
)

m = r_lot.split("_")[0]
b = r_lot.split("_")[1]


spec = {
    "name": m + "_" + b,
    "description": "Geometric + Psi4/" + m + "/" + b,
    "optimization_spec": {"program": "geometric", "keywords": None},
    "qc_spec": {
        "driver": "gradient",
        "method": m,
        "basis": b,
        "keywords": None,
        "program": "psi4",
    },
}

count = 0

try:
    ds_soc = client.get_collection("OptimizationDataset", cluster_collection)
except KeyError:
    print(
        """Collection with set of clusters that span the surface {} does not exist. Please create it first. Exiting...
    """.format(
            cluster_collection
        )
    )
    sys.exit(1)

try:
    ds_sm = client.get_collection("OptimizationDataset", mol_collection)
except KeyError:
    print(
        """Collection {} with the target molecules does not exist, please create it first. Exiting...
    """.format(
            mol_collection
        )
    )
    sys.exit(1)

soc_list = ds_soc.data.records

try:
    target_mol = ds_sm.get_record(smol_name, opt_lot).get_final_molecule()
    if target_mol is None:
                raise ValueError("The molecule is still being optimized. Please try again when the staus in complete.")
except KeyError:
    print(
        "{} is not optimized at the requested level of theory, please optimize them first\n".format(
            smol_name
        )
    )
    sys.exit(1)

for w in ds_soc.data.records:
    print("Processing cluster: {}".format(w))
    try:
        cluster = ds_soc.get_record(w, opt_lot).get_final_molecule()
    except KeyError:
        print(
            "{} is not optimized at the requested level of theory, please optimize it first\n".format(
                w
            )
        )
        continue

    opt_dset_name = smol_name + "_" + w

    try:
        ds_opt = client.get_collection("OptimizationDataset", opt_dset_name)
        c = len(ds_opt.status(collapse=False))
        count = count + int(c)
    except KeyError:
        pass

    out_file = Path("./site_finder/" + str(smol_name) + "_w/" + w + "/out_sampl.dat")

    if not out_file.is_file():
        out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(out_file, "w") as f:
        f.write(
            """        Welcome to the Molecular Sampler Converger! 
    
    Description: The molecular sampler converger optimizes random initial configurations
    of a small molecule around a  center molecule until at least 220 binding sites are found or
    all clusters of a set are sampled..
    
    Author: svogt, gbovolenta
    Data: 10/24/2020
    
    """
        )
    sampling(
        method,
        basis,
        program,
        tag,
        kw_id,
        opt_dset_name,
        opt_lot,
        rmsd_symm,
        rmsd_val,
        target_mol,
        cluster,
        out_file,
        client,
        sampling_shell,
        sampling_condition,
    )
    print("Total number of binding sites so far: {} ".format(count))
    ds_opt = client.get_collection("OptimizationDataset", opt_dset_name)
    ds_opt.add_specification(**spec, overwrite=True)
    ds_opt.save()
    c = ds_opt.compute(m + "_" + b, tag="refinement")
    count = count + int(c)
    with open(out_file, "a") as f:
        f.write(
            """
        Sending {} optimizations at {} level.""".format(
                c, r_lot
            )
        )
    if count > 220:
        break
