# Every file in k8s/ becomes one Kubernetes object. To deploy a new version, change the image tag in
# k8s/deployment.yaml: that is the only change a release needs here.
resource "kubernetes_manifest" "k8s" {
  for_each = fileset("${path.module}/k8s", "*.yaml")
  manifest = yamldecode(file("${path.module}/k8s/${each.value}"))
}
