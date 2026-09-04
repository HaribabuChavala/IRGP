{{- define "user-management-service.fullname" -}}
{{- printf "%s-user-management-service" .Release.Name -}}
{{- end -}}
