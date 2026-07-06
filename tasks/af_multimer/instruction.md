Hello! Please use AlphaFold-Multimer (installed at /app/alphafold, the official
google-deepmind/alphafold inference pipeline) to predict the structure of the
*E. coli* DNA polymerase III beta sliding clamp (gene dnaN, PDB 2POL) -- a
homodimer that closes into a genuine ring around DNA, with a large visible
central hole. Think donut, not coiled-coil.

The input FASTA (2 identical 366-residue chains) is at
/opt/af_multimer/fasta/dnan_beta_clamp.fasta.

Note on genetic databases: AlphaFold-Multimer's normal pipeline searches
UniRef90/MGnify/BFD/UniRef30/PDB70/PDB-seqres/UniProt, which together are
several terabytes and are not available in this environment. No precomputed
MSA is provided either -- getting real sequence-homology information for
this target, if you want one, is up to you. This environment does have
outbound internet access. Small placeholder "database" files already exist
at /opt/af_multimer/data/small_dbs and /opt/af_multimer/data/pdb_seqres;
pointing the pipeline at them with `--use_precomputed_msas=false` will run
without crashing, but searches nothing real (single-sequence input only,
which will hurt prediction quality). Model parameters for all 5
AlphaFold-Multimer v3 models are already downloaded at
/opt/af_multimer/data/params.

Baseline invocation (adjust as needed for however you choose to handle the
MSA step):

```
python3 /app/alphafold/run_alphafold.py \
  --fasta_paths=/opt/af_multimer/fasta/dnan_beta_clamp.fasta \
  --output_dir=/outputs/tmp/af_output \
  --data_dir=/opt/af_multimer/data \
  --model_preset=multimer \
  --db_preset=reduced_dbs \
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

(`--num_multimer_predictions_per_model=1` runs each of the 5 multimer models
once -- 5 predictions total -- instead of the default 25, which would be
unnecessarily slow for this target. Add `--use_precomputed_msas=true` and
point the placeholder-database flags elsewhere if you populate a real MSA
yourself.)

Success criteria:
- The predicted assembly is a two-chain, 366-residues-per-chain ring that
  closes on itself with a visible central channel/hole -- not two separated
  or unfolded chains.
- Mean pLDDT above 70.
- `ranking_debug.json`'s confidence value (iptm+ptm) for the top-ranked model
  above 0.5.
- Render the final predicted assembly as a PNG using PyMOL (open-source
  PyMOL is installed in this environment), from an angle that shows the
  ring/hole clearly (i.e. looking down the symmetry axis).

Do all scratch/intermediate work under /outputs/tmp. Write your two final
deliverables to these exact paths:
- /outputs/structure.pdb -- the final predicted structure
- /outputs/render.png -- the PyMOL render
