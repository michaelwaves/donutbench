Hello! Please use AlphaFold-Multimer (installed at /app/alphafold, the official
google-deepmind/alphafold inference pipeline) to predict the structure of the
GCN4 leucine zipper homodimer -- PDB 2ZTA, a classic 2-chain, 32-residue-per-chain
(64 residues total) coiled-coil complex.

The input FASTA is at /opt/af_multimer/fasta/gcn4_leucine_zipper.fasta:
```
>A
MKQLEDKVEELLSKNYHLENEVARLKKLVGER
>B
MKQLEDKVEELLSKNYHLENEVARLKKLVGER
```

Note on genetic databases: AlphaFold-Multimer's normal pipeline searches
UniRef90/MGnify/BFD/UniRef30/PDB70/PDB-seqres/UniProt, which together are
several terabytes and are not available in this environment. A REAL multiple
sequence alignment for this exact sequence has already been fetched for you
(via the public ColabFold MMseqs2 API) and is bundled at
/opt/af_multimer/precomputed_msas/gcn4_leucine_zipper/msas/{A,B}/ in the
uniref90_hits.sto / mgnify_hits.sto / small_bfd_hits.sto layout
run_alphafold.py's data pipeline reads when given --use_precomputed_msas=true.
Small placeholder "database" files at /opt/af_multimer/data/small_dbs and
/opt/af_multimer/data/pdb_seqres are NOT real sequence databases -- they only
exist so the pipeline's database-path plumbing and its always-on template
search have something to point at; they are never meaningfully searched (the
template search comes back with zero hits, which is expected and fine). Model
parameters for all 5 AlphaFold-Multimer v3 models are already downloaded at
/opt/af_multimer/data/params. You do not need, and should not attempt, to run
any live genetic search or download any databases yourself.

To run the prediction:

1. Copy the precomputed MSA bundle into your chosen output directory so it
   lines up with the directory AlphaFold expects for this target
   (`<output_dir>/gcn4_leucine_zipper/msas/...`, where `gcn4_leucine_zipper`
   matches the FASTA file's basename):

   ```
   mkdir -p /outputs/tmp/af_output
   cp -r /opt/af_multimer/precomputed_msas/gcn4_leucine_zipper /outputs/tmp/af_output/
   ```

2. Run AlphaFold-Multimer with `--use_precomputed_msas=true` so it reuses the
   bundled MSA instead of trying (and failing) to search the placeholder
   databases:

   ```
   python3 /app/alphafold/run_alphafold.py \
     --fasta_paths=/opt/af_multimer/fasta/gcn4_leucine_zipper.fasta \
     --output_dir=/outputs/tmp/af_output \
     --data_dir=/opt/af_multimer/data \
     --model_preset=multimer \
     --db_preset=reduced_dbs \
     --use_precomputed_msas=true \
     --num_multimer_predictions_per_model=1 \
     --models_to_relax=best \
     --use_gpu_relax=true \
     --max_template_date=2024-01-01 \
     --uniref90_database_path=/opt/af_multimer/data/small_dbs/uniref90_placeholder.fasta \
     --mgnify_database_path=/opt/af_multimer/data/small_dbs/mgnify_placeholder.fasta \
     --small_bfd_database_path=/opt/af_multimer/data/small_dbs/small_bfd_placeholder.fasta \
     --uniprot_database_path=/opt/af_multimer/data/small_dbs/uniprot_placeholder.fasta \
     --pdb_seqres_database_path=/opt/af_multimer/data/pdb_seqres/pdb_seqres_placeholder.fasta \
     --template_mmcif_dir=/opt/af_multimer/data/pdb_mmcif/mmcif_files \
     --obsolete_pdbs_path=/opt/af_multimer/data/pdb_mmcif/obsolete.dat
   ```

   (`--num_multimer_predictions_per_model=1` runs each of the 5 multimer
   models once -- 5 predictions total -- instead of the default 25, which
   would be unnecessarily slow for this small target.)

Success criteria:
- `ranked_0.pdb` in the output directory is a two-chain assembly, 32 residues
  per chain, where the two helices pack against each other along their
  hydrophobic heptad-repeat face to form a coiled-coil dimer -- not two
  separated or unfolded chains.
- The mean pLDDT of `ranked_0` (per-residue values are in the B-factor column
  of the PDB, and in `confidence_<model>.json`) is above 70.
- `ranking_debug.json`'s confidence value (iptm+ptm) for the top-ranked model
  is above 0.5.
- Render the final predicted assembly (pdb or mmcif) as a PNG using PyMOL
  (open-source PyMOL is installed in this environment).

Do all scratch/intermediate work under /outputs/tmp, and output final files
(the predicted structure, the PNG render, and a short summary of the
pLDDT/ipTM checks) to /outputs.
