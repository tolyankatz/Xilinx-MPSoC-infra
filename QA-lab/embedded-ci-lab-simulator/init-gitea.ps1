# Initialize Gitea with default settings
$postData = "db_type=sqlite3&db_host=localhost%3A3306&db_user=root&db_passwd=&db_name=gitea&ssl_mode=disable&db_schema=&charset=utf8&db_path=%2Fdata%2Fgitea%2Fgitea.db&app_name=Gitea%3A+Git+with+a+cup+of+tea&repo_root_path=%2Fdata%2Fgit%2Frepositories%2F&lfs_root_path=%2Fdata%2Fgit%2Flfs&run_user=git&domain=localhost&ssh_port=2222&http_port=3000&app_url=http%3A%2F%2Flocalhost%3A3000%2F&log_root_path=%2Fdata%2Fgitea%2Flog&admin_name=admin&admin_passwd=password&admin_confirm_passwd=password&admin_email=admin%40example.com"

$headers = @{
    "Content-Type" = "application/x-www-form-urlencoded"
}

try {
    $response = Invoke-WebRequest -Uri http://localhost:3000/install -Method POST -Headers $headers -Body $postData -UseBasicParsing
    Write-Host "Gitea initialization complete"
    Write-Host "Response: $($response.StatusCode)"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host "Status: $($_.Exception.Response.StatusCode)"
}
