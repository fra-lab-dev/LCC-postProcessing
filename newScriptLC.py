import argparse
import os
import rasterio
import numpy as np
import psycopg2
from scipy import ndimage






class createLCC:
    def __init__(self, conn, rasAI, outPath, baseName):
        self.conn = conn
        self.rasAI = rasterio.open(rasAI)
        self.baseName = f"LC_{baseName}"

        if not os.path.exists(outPath):
            os.makedirs(outPath)
        self.outPath = outPath

        self.N_A = 999

        # Imposta le proprietà dell'ambiente
        self.extent = self.rasAI.bounds
        self.cellSize = self.rasAI.res
        self.snapRaster = self.rasAI.filename

        # Imposta i percorsi dei file di input
        self.ait = self.get_table_data('ait')
        self.ait_l = self.get_table_data('ait_l')
        self.region = self.get_table_data('region')

        self.ancillary = self.get_table_data('ancillary')
        self.RulesOrdineCaricamento = self.get_table_data('RulesOrdineCaricamento')
        self.RulesXmatch = self.get_table_data('RulesXmatch')

        return


    def riclassifica_dati(self, dati, riclassifica):
        for vecchio_valore, nuovo_valore in riclassifica:
            dati[dati == vecchio_valore] = nuovo_valore
        return dati

    def load_raster(self, path):
        return rasterio.open(path)

    def lccRoads(self, bRas):
        print(self.lccRoads.__name__)

        # Apri il raster di input utilizzando rasterio
        with rasterio.open(self.rasAI.catalogPath) as src:
            # Ottieni le informazioni metadata del dataset
            meta = src.meta.copy()

            # Leggi i dati raster in un array NumPy
            data = src.read(1)

            # Definisci la riclassificazione
            riclassifica = [[20, 111], [21, 111], [23, 111], [31, 111], [32, 111], [33, 111], [34, 111], [41, 111],
                            [30, 112], [29, 112], [22, 112], [25, 112]]

            # Esegui la riclassificazione
            data = self.riclassifica_dati(data, riclassifica)

            # Crea un raster maschera
            maschera_dati = np.where((data == 20) | (data == 21) | (data == 23) | (data == 31) | (data == 32) |
                                    (data == 33) | (data == 34) | (data == 41) | (data == 30) | (data == 29) |
                                    (data == 22) | (data == 25), 1, 0)

            # Semplifica il raster maschera
            maschera_dati = ndimage.binary_opening(maschera_dati, iterations=1)
            maschera_dati = np.where(maschera_dati == 1, self.N_A, maschera_dati)

            # Applica la maschera al raster originale
            out_dati = np.where(bRas == self.N_A, maschera_dati, bRas)

            # Salva il raster di output
            meta.update(dtype=rasterio.uint8)
            with rasterio.open(f"{self.baseName}_{self.lccRoads.__name__}_rasMask.tif", "w", **meta) as dst:
                dst.write(out_dati.astype(rasterio.uint8), 1)

        return rasterio.open(f"{self.baseName}_{self.lccRoads.__name__}_rasMask.tif")
        
        
    def lcc112(self, bRas):
        print(self.lcc112.__name__)

        # Apri il raster di input utilizzando rasterio
        with rasterio.open(self.rasAI.catalogPath) as src:
            # Ottieni le informazioni metadata del dataset
            meta = src.meta.copy()

            # Leggi i dati raster in un array NumPy
            data = src.read(1)

            # Crea il raster di output
            out_data = np.where(data == 112, 112, self.N_A)

            # Semplifica il raster di output
            out_data = ndimage.binary_opening(out_data, iterations=1)

            # Applica il raster di output al raster di input
            final_data = np.where(bRas == self.N_A, out_data, bRas)

            # Salva il raster di output
            meta.update(dtype=rasterio.uint8)
            with rasterio.open(f"{self.baseName}_{self.lcc112.__name__}_rasMask.tif", "w", **meta) as dst:
                dst.write(final_data.astype(rasterio.uint8), 1)

        return rasterio.open(f"{self.baseName}_{self.lcc112.__name__}_rasMask.tif")

    def get_table_data(self, table_name):
        cur = self.conn.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        data = cur.fetchall()
        cur.close()
        return data
        
    def create_mask(self, ras):
        # Leggi i dati raster in un array NumPy
        data = ras.read(1)

        # Crea una maschera binaria
        mask = np.where(data != self.N_A, 1, 0)

        return mask

    def run(self):
        print(f"run() {self.rasAI.catalogPath}")

        self.delete_tmp = True
        base_elab = True
        final_cleaning = True

        rasMask = self.create_mask(self.rasAI)
        rasMask.save(f"{self.baseName}_rasMask")

        ### base elab

        lccRoads = self.lccRoads(rasMask) if base_elab else self.load_raster(f"{self.baseName}_lccRoads_rasMask")
        lcc3 = self.lcc3(lccRoads) if base_elab else self.load_raster(f"{self.baseName}_lcc3_rasMask")
        lcc111 = self.lcc111(lcc3) if base_elab else self.load_raster(f"{self.baseName}_lcc111_rasMask")
        lcc112 = self.lcc112(lcc111) if base_elab else self.load_raster(f"{self.baseName}_lcc112_rasMask")
        lcc121 = self.lcc121(lcc112) if base_elab else self.load_raster(f"{self.baseName}_lcc121_rasMask")
        lcc122 = self.lcc122(lcc121) if base_elab else self.load_raster(f"{self.baseName}_lcc122_rasMask")
        lccTrees2111 = self.lccTrees2111(lcc122) if base_elab else self.load_raster(f"{self.baseName}_lccTrees2111_rasMask")
        lccTrees2112 = self.lccTrees2112(lccTrees2111) if base_elab else self.load_raster(f"{self.baseName}_lccTrees2112_rasMask")
        lcc212 = self.lcc212(lccTrees2112) if base_elab else self.load_raster(f"{self.baseName}_lcc212_rasMask")
        lcc22 = self.lcc22(lcc212) if base_elab else self.load_raster(f"{self.baseName}_lcc22_rasMask")
        lcc32 = self.lcc32(lcc22) if base_elab else self.load_raster(f"{self.baseName}_lcc32_rasMask")

        ### Check Arboree

        lccCheckArb = self.lccCheckArb(lcc32) if base_elab else self.load_raster(f"{self.baseName}_lccCheckArb_rasMask")

        ### final cleaning

        if final_cleaning:
            shrink = self.shrink(lccCheckArb, 5, 999, 'MORPHOLOGICAL')
            outRas = shrink
        else:
            outRas = lccCheckArb

        outRas = self.repairNoData(outRas)

        self.exportRas(outRas, self.outPath, f"{self.baseName}.tif")

    def shrink(self, in_raster, number_cells, zone_values, shrink_method='DISTANCE'):
        print(f"shrink {in_raster.name} number_cells {number_cells}, zone_values {zone_values}, shrink_method {shrink_method}")

        # Leggi il raster di input
        with rasterio.open(in_raster) as src:
            arr = src.read(1)

        # Applica la funzione di shrink
        if shrink_method == 'DISTANCE':
            # Utilizza la funzione di shrink di numpy
            kernel = np.ones((number_cells, number_cells))
            arr = np.pad(arr, number_cells, mode='constant')
            arr = np.convolve2d(arr, kernel, mode='same')
            arr = arr[number_cells:-number_cells, number_cells:-number_cells]
        elif shrink_method == 'MORPHOLOGICAL':
            # Utilizza la funzione di morphological closing di scipy
            from scipy.ndimage import binary_closing
            arr = binary_closing(arr, structure=np.ones((number_cells, number_cells)))

        # Salva il risultato
        tmpBaseName = f"{self.baseName}_{self.shrink.__name__}{zone_values}"
        with rasterio.open(tmpBaseName, 'w', **src.meta) as dst:
            dst.write(arr, 1)

        # Elimina il raster di input se necessario
        if self.delete_tmp:
            os.remove(in_raster)        

def main():
    parser = argparse.ArgumentParser(description="Script post-processing Land Cover Mapping")
    parser.add_argument("--pathInf", type=str, help="Path to Inference map")
    parser.add_argument("--pathOut", type=str, help="Path to Output map")
    parser.add_argument("--output", type=str, help="Name of Output map")
    parser.add_argument("--tile", type=str, help="Tile to process")

    args = parser.parse_args()

    # Parametri di connessione al database Postgres
    host = "localhost"
    database = "nome_database"
    user = "nome_utente"
    password = "password"

    # Connessione al database
    conn = psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password
    )

    # Crea un cursore per eseguire query
    cur = conn.cursor()

    # Query per ottenere i dati dei tile
    query = "SELECT lotto, name FROM tiles ORDER BY lotto, name"
    cur.execute(query)

    # Ottieni i dati dei tile
    tiles = cur.fetchall()

    # Chiudi il cursore e la connessione
    cur.close()
    conn.close()

    path_to_inf = args.pathInf
    out_base_path = args.pathOut
    output_raster = args.output
    
    inference_path = os.path.dirname(path_to_inf)
    inferences = os.path.basename(path_to_inf)

    rasters = args.tile.split(',')

    over_write = True

    # Itera sui tile
    for tile in rasters:
        # Trova l'indice del tile nei dati
        idx = [i for i, x in enumerate(tiles) if x[1] == tile]

        # Se il tile non esiste, continua
        if len(idx) == 0:
            continue

        # Leggi i dati del tile
        with rasterio.open(os.path.join(inference_path, inferences)) as src:
            ras_ref = src.read(1)

        # Crea il percorso di output
        out_path = os.path.join(out_base_path, f"{output_raster}{3}_{tile}")
        out_lcc = os.path.join(out_path, f"LC_{tile}.tif")

        # Se il file di output esiste e non si vuole sovrascrivere, continua
        if os.path.exists(out_lcc) and not over_write:
            continue

        # Crea la cartella di output se non esiste
        if not os.path.exists(out_path):
            os.makedirs(out_path)

        # Esegui la classe createLCC
        create_lcc(conn, ras_ref, out_path, tile)

if __name__ == "__main__":
    main()
