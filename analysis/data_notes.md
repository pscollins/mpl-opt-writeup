# Run types

The default, standard configurations are:

* "tuple": tuple-flattening vs baseline
* "con": con-flattening vs baseline
* "aos": AOS-style container flattening vs baseline
* "soa": SOA-style container flattening vs baseline

We additionally have (for the sake of drilling down in particular sections):

* "tuple_vs_fixup:" test side is tuple-flattening, baseline enables "always post-fixup mode"
* "tuple_chunkify_one:" tuple-flattening vs baseline, with `-chunkify one` on both sides

# Previous runs

The runs in:
```
  "mlton_benchmarks_mlton_vs_mlton": {
    "aos": "test_aos_flatten_full_mlton_mlton:flattening-tests:75df6a4:20260816_153128.jsonl",
    "soa": "test_soa_flatten_full_mlton_mlton:flattening-tests:457f53e:20260816_173128.jsonl"
  },
  "parallel_bench_benchmarks_mlton_vs_mlton": {
    "aos": "mlton_aos_full_parallel_mlton:260816-124448:flattening-tests:c3def9c964dc7d927f01861817cdc614debfebfd:260816-124448.processed.jsonl",
    "soa": "mlton_soa_full_parallel_mlton:260816-143356:flattening-tests:c3def9c964dc7d927f01861817cdc614debfebfd:260816-143356.processed.jsonl"
  },
  "parallel_bench_benchmarks_mpl_vs_mpl": {
    "aos": "mpl_aos_full_parallel_mpl:260815-192835:flattening-tests:9f16c65c0980dae0805c9f131cdde030e8bcb885:260815-192835.processed.jsonl",
    "soa": "mpl_tuple_full_parallel_mpl:260816-031958:flattening-tests:e5b54c7d06312d90d49e3221644919f375693922:260816-031958.processed.jsonl"
  }
```
used `maxWidthSameType:4`

The new runs:
```
  "mlton_benchmarks_mlton_vs_mlton": {
    "aos": "test_aos_flatten_set_width_3:flattening-tests:8e04c8184:20260822_005802.jsonl",
    "soa": "test_soa_flatten_set_width_3:flattening-tests:8e04c8184:20260822_025807.jsonl"
  },
  "parallel_bench_benchmarks_mlton_vs_mlton": {
    "aos": "mlton_aos_set_width_3:260822-125845:flattening-tests:3855ae7a634096471da6aca8b30777d75010108d:260822-125845.processed.jsonl",
    "soa": "mlton_soa_set_width_3:260822-132730:flattening-tests:3855ae7a634096471da6aca8b30777d75010108d:260822-132730.processed.jsonl"
  },
  "parallel_bench_benchmarks_mpl_vs_mpl": {
    "aos": "mpl_aos_set_width_3:260822-135617:flattening-tests:3855ae7a634096471da6aca8b30777d75010108d:260822-135617.processed.jsonl",
    "soa": "mpl_soa_set_width_3:260822-145503:flattening-tests:3855ae7a634096471da6aca8b30777d75010108d:260822-145503.processed.jsonl"
  }
```

use `maxWidthSameType:3`
