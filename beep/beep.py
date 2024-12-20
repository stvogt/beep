try:
    import qcportal as ptl
except ModuleNotFoundError:
    import qcfractal.interface as ptl

import pandas as pd
import numpy as np
from tqdm import tqdm
from .exceptions import *

# Author: svogt, gbovolenta
# Date: 15.06.2021

class BindingParadise(object):
    """Data query QCPortal wrapper for the BEEP  database.

    Parameters
    ----------
    None

    Attributes
    ----------
    client : qcportal.client.FractalClient
        The FractalClient instance

    mol: str
        The supermolecule name.

    opt_lot: list
        The list of optimization methods for which the supermolecule has been optimized.


    df_be: Pandas.DataFrame
         The dataframe containing the binding energy values for the supermolecule.

    """

    def __init__(self, username, password):
        client = ptl.FractalClient(
            address="152.74.10.245:7777",
            verify=False,
            username=username,
            password=password,
        )
        self.client = client

    def molecules_list(self):
        """Lists all the available molecules:

        Parameters
        ----------
        None

        Returns
        -------
        list
            A list object which contains the available molecules."""

        client = self.client
        c = client.list_collections().loc["ReactionDataset"]
        molecules_list = []
        for row in c.index:
            if "be_" in row:
            #if "be_" and "W22" in row:
                r = str(row.split("_")[1]) + "_" + str(row.split("_")[2])
                if r not in molecules_list:
                    molecules_list.append(r)
        return molecules_list

    def set_molecule(self, mol):
        """Sets instance attribute molecule:

        Parameters
        ----------

        mol : str
            The selected molecule

        Returns
        -------
        None
        """

        print("Molecule set: {}".format(mol.upper()))
        self._mol = mol

    def get_optimization_methods(self):
        """Lists the optimization methods for which the molecule has been optimized:

        Parameters
        ----------

        None

        Returns
        -------
        list
            A list object with the available optimization methods."""

        client = self.client

        try:
            self._mol
        except AttributeError:
            raise MoleculeNotSetError()

        mol = self._mol
        c = client.list_collections("ReactionDataset")
        be_col = [row for row in c.index if "be_" + mol + "_05_" in row[1]]
        opt_lot = [x[1].split("_")[-1].upper() for x in be_col]
        self._opt_lot_list = opt_lot
        print("List of optimization methods: {}".format(opt_lot))
        return opt_lot

    def load_data(self, opt_lot=None, progress_bar=True):
        """Loads binding energy data for the selected molecule:

        Parameters
        ----------

        opt_lot : str, optional
            The selected optimization method. When ``opt_lot = None``, sets the first available level of theory.
        Returns
        -------
        None

        Raises
        -------
        MoleculeNotSetError
            If molecule is not set to the instance.
        OptimizationMethodNotSetError
            If Optimization Method is not set yet.
        """

        client = self.client

        try:
            self._opt_lot_list
        except AttributeError:
            raise OptimizationMethodNotSetError()

        if opt_lot == None:
            opt_lot = self._opt_lot_list[0]

        ds_be_list = []
       
        if progress_bar:
            ran = tqdm(range(1,20))
        else:
            ran = range(1,20)

        for i in ran:
            be_name = "be_" + self._mol + "_" + "%02d" % i + "_" + opt_lot
            try:
                ds_be = client.get_collection("ReactionDataset", be_name)
            except KeyError:
                continue
            ds_be_list.append(ds_be)
        self._ds_set = ds_be_list
        self._opt_lot = opt_lot

    def get_methods(self, print_out = True):
        """Gets the available binding energy methods:

        Parameters
        ----------
        print_out: bool, prints out the available binding energy methods.

        Returns
        -------
        dict
            A dictionary object with method and corresponding stoichiometry.
        """

        method_dict = {}
        client = self.client
        mol = self._mol
        ds_be = self._ds_set[-1]
        method_info = ds_be.data.history
        for m in method_info:
            method = m[2]
            stoich = m[-1]
            method_dict[method] = stoich
        if print_out:
            print(
                "The available binding energy methods for {} geometries are : {}".format(
                    self._opt_lot, [x for x in method_dict.keys()]
                )
            )
        return method_dict

    def get_zpve_dictionary(self):
        """Returns a list with Zero Point Vibrational Energy correction factors. These have been obtained at HF-3c/MINIX level of theory, using a linear model. In order to correct the binding energy (BE), use:

        ``bp = BindingParadise('username ','password')
          BE = bp.get_zpve_dictionary()[0] * BE + bp.get_zpve_correction()[1]``

        Parameters
        ----------

        None

        Returns
        -------
        list
            A list with with Zero Point Vibrational Energy correction factors.
        """
        try:
            self._mol
        except AttributeError:
            raise MoleculeNotSetError()

        #return zpve_dictionary[self._mol]
        return None


    def get_values(self, method=None, zpve=False, progress_bar=True):
        """Gets binding energy values for a given method.

        Parameters
        ----------

        method : str or list, optional
            The methods used to compute the binding energies.  When ``method = None``, sets the first available level of theory. Use get_methods to list the available binding energy methods.
        zpve : bool, optional
            Returns the binding energy values corrected for Zero Point Vibrational Energy.
        progress_bar : bool, optional
            Display a progress bar while querying the data from the database.

        Returns
        -------
        Pandas.DataFrame
            A Pandas.DataFrame object containing the binding energy values.
        """

        try:
            self._mol
        except AttributeError:
            raise MoleculeNotSetError()

        try:
            self._ds_set
        except AttributeError:
            raise DataNotLoadedError()

        en_val_list = []
        method_dict = self.get_methods(print_out = False)

        if not method:
            method = list(method_dict.keys())[0]
        stoich = method_dict[method]

        if progress_bar:
            ran = tqdm(self._ds_set)
        else:
            ran = self._ds_set

        for ds in ran:
            try:
                en_val = ds.get_values(stoich=stoich, method=method)
            except KeyError:
                continue
            en_val_list.append(en_val)
        df_be = pd.concat(en_val_list).dropna()

        #if zpve:
        #    m, b = zpve_dictionary[self._mol]
        #    df_be[str(method.upper()) + " + ZPVE"] = m * df_be + b

        self._df_be = df_be
        return df_be

    def get_molecules(self, be_method=None):
        """Help on method get_molecule in class BEEP:

        Parameters
        ----------

        be_method : str or list, optional
            The methods used to compute the binding energies, that are included in the return dataframe.  When ``method = None``, sets the first available level of theory. 

        Returns
        -------
        Pandas.DataFrame
            A Pandas.DataFrame object containing the binding energy values and molecule objects.
        """

        mol_dict = {}
        mol_list = []
        name_list = []

        method_dict = self.get_methods(print_out=False)

        if not be_method:
            be_method = list(method_dict.keys())[0]

        stoich = method_dict[be_method]

        for ds in self._ds_set:
            df = ds.get_entries()
            df.drop_duplicates(subset = ['name'], keep = 'first', inplace = True)
            mol_list.extend(df['molecule'].tolist())
            name_list.extend(df['name'].tolist())
        mol_obj_list = self.client.query_molecules(mol_list)
        for i in range(len(mol_obj_list)):
            mol_dict[name_list[i]] = {"molecule": mol_obj_list[i]}
        df_mol = pd.DataFrame.from_dict(mol_dict, orient="index")
        return pd.concat([self.get_values(method=be_method), df_mol], axis=1).dropna()


    def visualize(self, methods=None):  # bin como opcion (numero)
        """Help on method visualize in class BEEP:

        Parameters
        ----------

        collection_type : str
            The collection type to be accessed
        name : str
            The name of the collection to be accessed
        full_return : bool, optional
            Returns the full server response if True that contains additional metadata.
        include : QueryListStr, optional
            Return only these columns.
        exclude : QueryListStr, optional
            Return all but these columns.
        Returns
        -------
        Collection
            A Collection object if the given collection was found otherwise returns `None`.
        """

        import matplotlib.pyplot as plt
        import numpy as np
        import math
        import qcelemental as qcel

        if not method:
            method = list(method_dict.keys())[0]

        stoich = method_dict[method]

        method_base = method

        df_be = self._df_be
        mol = self._mol
        nbins = 12

        bins_K = np.arange(
            min(df_be.min(axis=1)), 1, 0.3
        ) * qcel.constants.conversion_factor("kcal/mol", "K")

        fig = plt.figure(figsize=(12, 10))
        fig.subplots_adjust(hspace=0.8)
        for i in range(len(methods)):
            v_K = df_be[
                methods[i] + "/def2-tzvp"
            ].values * qcel.constants.conversion_factor("kcal/mol", "K")

            # Counting nan elements in order to exclude them from structures' count:
            n = list(map(lambda x: 0.0 if math.isnan(x) else x, v_K))
            nan_structs = n.count(0.0)

            fig.add_subplot(len(methods), 1, i + 1)

            plt.hist(
                v_K,
                bins=nbins,
                edgecolor="black",
                density=False,
                color="blue",
                alpha=0.3,
            )
            plt.xlabel("$E_b$ / $K$ ", size=15)
            plt.ylabel("frequency number", size=15)
            plt.title(
                "{}, {}/def2-tzvp Binding Energy values, {} optimized structures".format(
                    mol.upper(), methods[i], str(len(v_K) - nan_structs)
                ),
                size=16,
            )
        plt.show()

    def get_sets(self, methods=None):
        """Gets a list of all ReactionDatasets for the selected molecule.

        Parameters
        ----------

        method : str or list, optional
            The methods used to compute the binding energies.  When ``method = None``, sets the first available level of theory. Use get_methods to list the available binding energy methods.

        Returns
        -------
        list
            A list object containing ReactionDatasets for the selected molecule.
        """

        return self._ds_set


if __name__ == "__main__":
    print(BindingParadies())
