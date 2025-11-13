
import os
import json

# Download refGene table from UCSC
os.system("wget http://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/refGene.txt.gz")
os.system("gunzip refGene.txt.gz")


def parse_ucsc_refgene(filename='refGene.txt'):
    genes = {}
    
    with open(filename, 'r') as f:
        for line in f:
            fields = line.strip().split('\t')
            gene_symbol = fields[12]  # Gene symbol
            chrom = fields[2]  # Chromosome
            start = int(fields[4])  # txStart
            end = int(fields[5])  # txEnd
            
            # Keep the gene with largest span if duplicates
            if gene_symbol not in genes or (end - start) > (genes[gene_symbol]['end'] - genes[gene_symbol]['start']):
                genes[gene_symbol] = {
                    'chromosome': chrom,
                    'start': start,
                    'end': end
                }
    
    return genes

genes = parse_ucsc_refgene()
with open('human_genes.json', 'w') as f:
    json.dump(genes, f, indent=2)

os.system("rm refGene.txt")
os.system("mv human_genes.json ../cholestrack/media/misc")