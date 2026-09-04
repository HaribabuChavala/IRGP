{{- define "report-platform.fullname" -}}
{{- printf "%s" .Release.Name -}}
{{- end -}}

{{- define "report-platform.labels" -}}
app.kubernetes.io/name: {{ include "report-platform.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: Helm
chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}
