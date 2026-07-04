---
title:   When the Snapshot Lives on the Disk That Died
date:    Jul 2026
tags:    Storage, Kubernetes
summary: Why CSI snapshots on local storage don't protect you from node failure — and how chunked offload to object storage fixes it.
related: https://github.com/cloudnativestorage/topolvm
minutes: 5
---

Local-path storage is the fastest disk a Kubernetes pod can get: TopoLVM
carves logical volumes straight out of the node's LVM volume group, so a
database gets NVMe-class latency with no network hop. The price is locality —
the volume exists on exactly one node, and when that node dies, the data goes
with it.

## The snapshot trap

The CSI spec has an answer for data protection: `VolumeSnapshot`. But on a
local-storage driver, the naive implementation snapshots the LV *into the
same volume group* — the copy lives on the same physical disk as the
original. It protects you from a bad deploy or a fat-fingered `DELETE`, and
from absolutely nothing else. Node gone, snapshot gone.

## Offloading snapshots with restic

The fix is to make the snapshot durable somewhere the node failure can't
reach: object storage. In the extended TopoLVM driver, a gRPC snapshot
service sits in the CSI workflow. When a `VolumeSnapshot` is requested, it:

1. takes a crash-consistent LVM snapshot for a stable read view,
2. chunks the volume contents and uploads them with restic to any
   S3-compatible bucket — deduplicated across snapshots, so daily snapshots
   of a mostly-static volume cost almost nothing,
3. releases the local LVM snapshot once the upload is verified.

Restore is the mirror image: a new empty LV on whatever node has capacity,
repopulated chunk by chunk from the repository.

    # request a snapshot — the driver handles chunking + offload
    kubectl apply -f - <<EOF
    apiVersion: snapshot.storage.k8s.io/v1
    kind: VolumeSnapshot
    metadata:
      name: pg-data-before-upgrade
    spec:
      volumeSnapshotClassName: topolvm-restic
      source:
        persistentVolumeClaimName: pg-data
    EOF

## Watching it in production

Snapshot pipelines fail quietly — a stuck upload looks identical to a slow
one until you miss a recovery point. Prometheus exporters on the snapshot
service track upload throughput, chunk cache hits, and end-to-end snapshot
duration, so a stalled offload pages someone before it becomes a story about
data loss.

The result: local-disk performance with off-node durability — the property
hybrid and on-prem clusters actually need.
