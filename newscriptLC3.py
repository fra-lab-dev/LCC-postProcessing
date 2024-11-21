import argparse
import os
import rasterio
import numpy as np
from scipy.signal import convolve2d
from scipy.ndimage import label, find_objects, binary_closing
import psycopg2


def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,  # Aggiungi il numero di porta qui
        database="nome_database",
        user="nome_utente",
        password="password"
    )
    return conn

class RasterProcessor:
    def __init__(self, base_name, delete_tmp=False):
        self.baseName = base_name
        self.delete_tmp = delete_tmp

    def shrink(self, arr, number_cells, zone_values, shrink_method='DISTANCE'):
        """
        Shrink the raster by a specified number of cells using the specified method.

        Parameters:
        arr (np.ndarray): Input raster as a numpy array.
        number_cells (int): Number of cells to shrink.
        zone_values (int): Values to be considered for shrinking.
        shrink_method (str): Method to use for shrinking ('DISTANCE' or 'MORPHOLOGICAL').

        Returns:
        np.ndarray: Shrunk raster as a numpy array.
        """
        print(f"shrink {zone_values} number_cells {number_cells}, shrink_method {shrink_method}")

        # Apply the shrink function
        if shrink_method == 'DISTANCE':
            # Use numpy's shrink function
            kernel = np.ones((number_cells, number_cells))
            arr = np.pad(arr, number_cells, mode='constant', constant_values=0)
            arr = convolve2d(arr, kernel, mode='same')
            arr = arr[number_cells:-number_cells, number_cells:-number_cells]
        elif shrink_method == 'MORPHOLOGICAL':
            # Use scipy's morphological closing function
            arr = binary_closing(arr, structure=np.ones((number_cells, number_cells)))

        return arr

    
    def reclassify_raster(arr, riclassifica):
        reclassified_arr = np.copy(arr)
        for old_value, new_value in riclassifica:
            reclassified_arr[arr == old_value] = new_value
        return reclassified_arr


    def symplyRaster(self, arr, min_aggragate_cells=1):
        """
        Simplify the raster by removing small isolated regions.

        Parameters:
        arr (np.ndarray): Input raster as a numpy array.
        min_aggragate_cells (int): Minimum number of cells to retain a region.

        Returns:
        np.ndarray: Simplified raster as a numpy array.
        """
        # Label connected regions of the array
        labeled_array, num_features = label(arr)

        # Find objects (slices) in the labeled array
        objects = find_objects(labeled_array)

        # Create an output array to store the simplified raster
        simplified_arr = np.copy(arr)

        for i, obj in enumerate(objects):
            # Calculate the size of each object
            size = np.sum(labeled_array[obj] == (i + 1))
            if size < min_aggragate_cells:
                # Remove small isolated regions
                simplified_arr[labeled_array == (i + 1)] = 0

        return simplified_arr

    def lccRoads(self, mask_array, conn):
        """
        Process the raster to identify and reclassify road-related values.

        Parameters:
        mask_array (np.ndarray): Input raster as a numpy array.
        conn (psycopg2.connection): Connection to the PostgreSQL database.

        Returns:
        np.ndarray: Reclassified and processed raster as a numpy array.
        """

        # Fetch reclassification values from the database
        cursor = conn.cursor()
        cursor.execute("SELECT orig, dest FROM lccreclass WHERE grp LIKE 'roads'")
        riclassifica = cursor.fetchall()
        cursor.close()

        # Reclassify the raster using the dedicated function
        reclassified_arr = self.reclassify_raster(mask_array, riclassifica)

        # Simplify the raster
        maskRasSimply = self.symplyRaster(reclassified_arr, min_aggragate_cells=1)

        # Apply the condition
        maskRasSimply = np.where(maskRasSimply == 1, self.N_A, maskRasSimply)



        outCon = np.where(mask_array == self.N_A, maskRasSimply, mask_array)

        return outCon


    def creaFcMask_lcc3(self, arr, values, new_value):
        """
        Create a mask for the specified values and reclassify them to a new value.

        Parameters:
        arr (numpy.ndarray): Input raster array.
        values (list): List of values to be reclassified.
        new_value (int): New value to assign to the specified values.

        Returns:
        numpy.ndarray: Reclassified raster array.
        """
        mask = np.isin(arr, values)
        reclassified_arr = np.where(mask, new_value, arr)
        return reclassified_arr
    
    def lcc3(self, mask_array, conn):
        """
        Elabora il raster per identificare e riclassificare i valori relativi a lcc3.

        Parametri:
        mask_array (numpy.ndarray): Input raster array.
        conn (psycopg2.connection): Connessione al database PostgreSQL.

        Ritorna:
        numpy.ndarray: Reclassified and processed raster array.
        """

        # Recupera i valori di riclassificazione dal database
        cursor = conn.cursor()
        cursor.execute("SELECT orig, dest FROM rccreclass WHERE grp LIKE 'lcc3'")
        riclassifica = cursor.fetchall()
        cursor.close()

        orig_list = [row[0] for row in riclassifica]

        # Riclassifica il raster utilizzando la funzione dedicata
        reclassified_arr = self.creaFcMask_lcc3(mask_array, orig_list, riclassifica)

        # Semplifica il raster
        maskRasSimply = self.symplyRaster(reclassified_arr, min_aggragate_cells=2)

        # Applica la condizione
        maskRasSimply = np.where(maskRasSimply == 1, self.N_A, maskRasSimply)

        outCon = np.where(mask_array == self.N_A, maskRasSimply, mask_array)

        return outCon


    def run(self, rasAI, N_A, conn):
        print(f"run() {rasAI}")

        self.delete_tmp = True
        base_elab = True
        final_cleaning = True

        with rasterio.open(rasAI) as src:
            arr = src.read(1)
            mask = np.where(arr != 0, N_A, 0)

        mask_path = f"{self.baseName}_rasMask.tif"
        with rasterio.open(mask_path, 'w', **src.meta) as dst:
            dst.write(mask, 1)

        ### base elab
        lccRoads = self.lccRoads(mask_path,conn)
        lcc3 = self.lcc3(lccRoads)
        # lcc111 = self.lcc111(lcc3) if base_elab else f"{self.baseName}_lcc111_rasMask.tif"
        # lcc112 = self.lcc112(lcc111) if base_elab else f"{self.baseName}_lcc112_rasMask.tif"
        # lcc121 = self.lcc121(lcc112) if base_elab else f"{self.baseName}_lcc121_rasMask.tif"
        # lcc122 = self.lcc122(lcc121) if base_elab else f"{self.baseName}_lcc122_rasMask.tif"
        # lccTrees2111 = self.lccTrees2111(lcc122) if base_elab else f"{self.baseName}_lccTrees2111_rasMask.tif"
        # lccTrees2112 = self.lccTrees2112(lccTrees2111) if base_elab else f"{self.baseName}_lccTrees2112_rasMask.tif"
        # lcc212 = self.lcc212(lccTrees2112) if base_elab else f"{self.baseName}_lcc212_rasMask.tif"
        # lcc22 = self.lcc22(lcc212) if base_elab else f"{self.baseName}_lcc22_rasMask.tif"
        # lcc32 = self.lcc32(lcc22) if base_elab else f"{self.baseName}_lcc32_rasMask.tif"

        ### Check Arboree
        # lccCheckArb = self.lccCheckArb(lcc32) if base_elab else f"{self.baseName}_lccCheckArb_rasMask.tif"

        ### final cleaning
        # if final_cleaning:
        #     shrink = self.shrink(lccCheckArb, 5, 999, 'MORPHOLOGICAL')
        #     outRas = shrink

def main():
    parser = argparse.ArgumentParser(description="Script post-processing Land Cover Mapping")
    parser.add_argument("--pathInf", type=str, help="Path to Inference map")
    parser.add_argument("--pathOut", type=str, help="Path to Output map")
    parser.add_argument("--output", type=str, help="Name of Output map")
    parser.add_argument("--tile", type=str, help="Tile to process")

    args = parser.parse_args()

    conn = get_db_connection()


    # Example usage of RasterProcessor
    processor = RasterProcessor(base_name=args.output)
    processor.run(args.pathInf, N_A=1, conn=conn)  # Assuming N_A is 1 for this example

if __name__ == "__main__":
    main()