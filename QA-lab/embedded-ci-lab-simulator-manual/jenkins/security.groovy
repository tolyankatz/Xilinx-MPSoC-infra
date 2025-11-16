import jenkins.model.*
import hudson.security.*

def instance = Jenkins.get()

// Check if the security realm is the one we expect
if (instance.getSecurityRealm() instanceof HudsonPrivateSecurityRealm) {
  def realm = instance.getSecurityRealm()
  
  // Create the admin user only if they don't already exist
  if (!realm.getUser('admin')) {
    println "--> Creating Jenkins admin user"
    def user = realm.createAccount('admin', 'admin') // Creates user 'admin' with password 'admin'
    user.setFullName('Admin User')
    user.save()
  } else {
    println "--> Jenkins admin user already exists"
  }
}