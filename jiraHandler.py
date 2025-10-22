from jira import JIRA, JIRAError
from loguru import logger
from rich.console import Console
from rich.progress import track
import sys

# Configure loguru logger
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"  # Changed to DEBUG for more detailed output
)

# Initialize rich console
console = Console()

class JiraHandler:
    def __init__(self, server_url, personal_access_token):
        #options = {'server': server_url}
        try:
            if personal_access_token:
                # Use Personal Access Token
                logger.info("Personal Access Token provided, authenticating...")
                self.jira = JIRA(server=server_url, token_auth=personal_access_token, validate=True)
                logger.success("Successfully connected to JIRA")
            else:
                raise ValueError("Either personal_access_token or both username and api_token must be provided")
        except JIRAError as e:
            logger.error(f"Failed to connect to JIRA: {e}")
            self.jira = None

    def get_issues(self, jql_query, max_results=None):
        if not self.jira:
            logger.error("JIRA connection not established.")
            return []
        
        all_issues = []
        start_at = 0
        max_per_request = 100  # JIRA's recommended batch size
        
        logger.info(f"Starting to fetch issues with JQL: {jql_query}")
        
        try:
            while True:
                logger.debug(f"Fetching issues {start_at} to {start_at + max_per_request}...")
                
                # Fetch a batch of issues
                issues_batch = self.jira.search_issues(
                    jql_query, 
                    startAt=start_at, 
                    maxResults=max_per_request,
                    fields="fixVersions, summary, status, key, issuetype"
                )
                
                if not issues_batch:
                    break
                
                all_issues.extend(issues_batch)
                logger.info(f"Retrieved {len(issues_batch)} issues. Total so far: {len(all_issues)}")
                
                # Check if we've reached the maximum or if there are no more issues
                if max_results and len(all_issues) >= max_results:
                    all_issues = all_issues[:max_results]
                    break
                
                if len(issues_batch) < max_per_request:
                    # Last batch - no more issues to fetch
                    break
                
                start_at += max_per_request
            
            logger.success(f"Total issues retrieved: {len(all_issues)}")
            return all_issues
            
        except JIRAError as e:
            logger.error(f"Failed to retrieve issues: {e}")
            return all_issues  # Return what we got so far
        
    # I want to check if each issue has the fix version
    def issue_has_fix_version(self, issue, fix_version):
        for version in issue.fields.fixVersions:
            if version.name == fix_version:
                self.issue_remove_fix_version(issue, fix_version)
                return True
        return False
    
    def can_edit_fix_versions(self, issue):
        """Check if the issue allows editing of fix versions"""
        try:
            # Get the edit metadata for this issue
            edit_meta = self.jira.editmeta(issue.key)
            
            # Check if fixVersions field is editable
            if 'fixVersions' in edit_meta['fields']:
                return True
            return False
        except Exception as e:
            logger.warning(f"Could not check edit permissions for {issue.key}: {e}")
            return False
    
    # I want to remove the fix version of the issue
    def issue_remove_fix_version(self, issue, fix_version):
        try:
            # Get current fix versions and filter out the one we want to remove
            current_fix_versions = [{"name": fv.name} for fv in issue.fields.fixVersions if fv.name != fix_version]
            
            # First try the standard update method
            issue.update(fields={"fixVersions": current_fix_versions})
            logger.success(f"Removed fix version '{fix_version}' from issue {issue.key}")
            
        except JIRAError as e:
            logger.warning(f"Standard update failed for {issue.key}: {e}")
            # Always try alternative approach when standard fails
            self._try_alternative_fix_version_removal(issue, fix_version)
        except Exception as e:
            logger.warning(f"Unexpected error during standard update for {issue.key}: {e}")
            # Always try alternative approach when standard fails
            self._try_alternative_fix_version_removal(issue, fix_version)
    
    def _try_alternative_fix_version_removal(self, issue, fix_version):
        """Alternative approach for issues where direct field update is not allowed"""
        try:
            issue_type = getattr(issue.fields, 'issuetype', {})
            issue_type_name = getattr(issue_type, 'name', 'Unknown') if issue_type else 'Unknown'
            status_name = getattr(issue.fields.status, 'name', 'Unknown') if hasattr(issue.fields, 'status') else 'Unknown'
            
            logger.info(f"Trying alternative removal methods for {issue.key} (type: {issue_type_name}, status: {status_name})")
            
            # Get available transitions for this issue
            transitions = self.jira.transitions(issue)
            logger.debug(f"Available transitions for {issue.key}: {[t['name'] for t in transitions]}")
            
            if not transitions:
                logger.warning(f"No transitions available for {issue.key}")
                return
            
            # Try different approaches in order of preference
            approaches = [
                # Look for explicit edit transitions
                [t for t in transitions if 'edit' in t['name'].lower()],
                # Look for update transitions
                [t for t in transitions if 'update' in t['name'].lower()],
                # Look for reopen transitions (common for closed issues)
                [t for t in transitions if 'reopen' in t['name'].lower()],
                # Look for any transition that might allow field updates (common transition names)
                [t for t in transitions if any(keyword in t['name'].lower() for keyword in ['modify', 'change', 'start', 'progress'])],
                # As a last resort, try all available transitions
                transitions
            ]
            
            current_fix_versions = [{"name": fv.name} for fv in issue.fields.fixVersions if fv.name != fix_version]
            logger.debug(f"Target fix versions after removal: {[fv['name'] for fv in current_fix_versions]}")
            
            for i, approach_transitions in enumerate(approaches):
                if not approach_transitions:
                    continue
                    
                approach_name = ["edit transitions", "update transitions", "reopen transitions", "modify/change transitions", "all transitions"][i]
                logger.debug(f"Trying approach {i+1}: {approach_name}")
                
                for transition in approach_transitions[:5]:  # Try first 5 transitions of each approach
                    try:
                        logger.debug(f"Attempting to remove fix version using transition '{transition['name']}' (ID: {transition['id']})")
                        
                        # Try the transition with fix version update
                        self.jira.transition_issue(
                            issue.key,
                            transition['id'],
                            fields={"fixVersions": current_fix_versions}
                        )
                        logger.success(f"Successfully removed fix version '{fix_version}' from issue {issue.key} using transition '{transition['name']}'")
                        return  # Success!
                        
                    except JIRAError as te:
                        logger.debug(f"Transition '{transition['name']}' failed: {te}")
                        continue
                    except Exception as te:
                        logger.debug(f"Unexpected error with transition '{transition['name']}': {te}")
                        continue
            
            # If all transition approaches failed, try some workarounds
            logger.debug("All transition approaches failed. Trying additional workarounds...")
            
            # Try 1: Direct update with minimal fields and different notification settings
            workarounds = [
                {"fields": {"fixVersions": current_fix_versions}, "notify": False},
                {"fields": {"fixVersions": current_fix_versions}, "notify": True},
                {"fields": {"fixVersions": current_fix_versions}},  # No notify parameter
            ]
            
            for i, update_params in enumerate(workarounds):
                try:
                    logger.debug(f"Trying workaround {i+1}: direct update with params {update_params}")
                    issue.update(**update_params)
                    logger.success(f"Successfully removed fix version '{fix_version}' from issue {issue.key} using direct update workaround {i+1}")
                    return
                except Exception as final_e:
                    logger.debug(f"Workaround {i+1} failed: {final_e}")
                    continue
            
            # Final attempt: Try to reopen the issue first, then update
            reopen_transitions = [t for t in transitions if 'reopen' in t['name'].lower()]
            if reopen_transitions and status_name.lower() in ['closed', 'resolved', 'done']:
                original_status = status_name  # Remember original status
                reopened_successfully = False
                fix_version_removed = False
                
                try:
                    logger.debug(f"Attempting to reopen issue {issue.key} (original status: {original_status})...")
                    self.jira.transition_issue(issue.key, reopen_transitions[0]['id'])
                    logger.success(f"Issue {issue.key} reopened successfully")
                    reopened_successfully = True
                    
                    # Now try to update the fix version with different notification approaches
                    update_approaches = [
                        {"fields": {"fixVersions": current_fix_versions}},  # Default (with notifications)
                        {"fields": {"fixVersions": current_fix_versions}, "notify": True},  # Explicit notifications
                    ]
                    
                    for i, update_params in enumerate(update_approaches):
                        try:
                            logger.debug(f"Trying to update fix versions after reopen, approach {i+1}")
                            issue.update(**update_params)
                            logger.success(f"Successfully removed fix version '{fix_version}' from issue {issue.key} after reopening")
                            fix_version_removed = True
                            break
                        except Exception as update_e:
                            logger.debug(f"Update approach {i+1} after reopen failed: {update_e}")
                            continue
                    
                    # If direct update failed, check if the reopen itself included the fix version change
                    if not fix_version_removed:
                        logger.debug("Checking if fix version was already removed during reopen transition...")
                        issue.reload()  # Refresh issue data
                        current_versions = [fv.name for fv in issue.fields.fixVersions]
                        if fix_version not in current_versions:
                            logger.success(f"Fix version '{fix_version}' was successfully removed from issue {issue.key} during reopen transition")
                            fix_version_removed = True
                        else:
                            logger.warning(f"Issue {issue.key} was reopened but fix version '{fix_version}' is still present")
                    
                    # Try to restore original status if we successfully reopened
                    if reopened_successfully:
                        self._restore_original_status(issue, original_status, fix_version_removed)
                        
                    if fix_version_removed:
                        return
                        
                except Exception as reopen_e:
                    logger.debug(f"Reopen approach failed: {reopen_e}")
                    # Still try to restore status if we managed to reopen but failed later
                    if reopened_successfully:
                        self._restore_original_status(issue, original_status, fix_version_removed)
            
            logger.error(f"All removal methods failed for {issue.key}. The issue may have workflow restrictions that prevent fix version modifications.")
            
            # Final verification: Check if the fix version was actually removed despite errors
            try:
                issue.reload()  # Refresh issue data from server
                current_versions = [fv.name for fv in issue.fields.fixVersions]
                if fix_version not in current_versions:
                    logger.success(f"SUCCESS: Fix version '{fix_version}' was actually removed from issue {issue.key} despite reported errors!")
                    return
                else:
                    logger.error(f"CONFIRMED: Fix version '{fix_version}' is still present on issue {issue.key}")
            except Exception as verify_e:
                logger.warning(f"Could not verify final state of {issue.key}: {verify_e}")
                
        except Exception as e:
            logger.error(f"Alternative removal method setup failed for {issue.key}: {e}")

    def _restore_original_status(self, issue, original_status, operation_successful):
        """Restore the issue to its original status after performing operations"""
        try:
            logger.debug(f"Attempting to restore issue {issue.key} to original status: {original_status}")
            
            # Get current transitions to find the right one to restore status
            current_transitions = self.jira.transitions(issue)
            logger.debug(f"Available transitions for status restoration: {[t['name'] for t in current_transitions]}")
            
            # Look for transitions that would restore to the original status
            target_transitions = []
            
            # Common transition patterns to restore to closed/resolved/done states
            if original_status.lower() == 'closed':
                target_transitions = [t for t in current_transitions if any(keyword in t['name'].lower() 
                                    for keyword in ['close', 'resolve', 'done', 'complete'])]
            elif original_status.lower() == 'resolved':
                target_transitions = [t for t in current_transitions if any(keyword in t['name'].lower() 
                                    for keyword in ['resolve', 'close', 'done', 'complete'])]
            elif original_status.lower() == 'done':
                target_transitions = [t for t in current_transitions if any(keyword in t['name'].lower() 
                                    for keyword in ['done', 'complete', 'close', 'resolve'])]
            
            # If no specific transitions found, try any transition that contains the original status name
            if not target_transitions:
                target_transitions = [t for t in current_transitions if original_status.lower() in t['name'].lower()]
            
            if target_transitions:
                # Try the first matching transition
                transition = target_transitions[0]
                logger.debug(f"Using transition '{transition['name']}' to restore to {original_status}")
                
                self.jira.transition_issue(issue.key, transition['id'])
                
                if operation_successful:
                    logger.success(f"Issue {issue.key} restored to original status '{original_status}' after successful fix version removal")
                else:
                    logger.info(f"Issue {issue.key} restored to original status '{original_status}' (fix version removal was unsuccessful)")
            else:
                logger.warning(f"Could not find appropriate transition to restore {issue.key} to status '{original_status}'")
                logger.info(f"Available transitions were: {[t['name'] for t in current_transitions]}")
                
        except Exception as restore_e:
            logger.warning(f"Failed to restore issue {issue.key} to original status '{original_status}': {restore_e}")
            if operation_successful:
                logger.info(f"Note: Fix version was successfully removed from {issue.key}, but status restoration failed")


# Main execution
logger.info("Starting JIRA Fix Version Removal Script")

jiraHandler = JiraHandler("https://rb-tracker.bosch.com/tracker13", "<pat>")

# JQL Query setup
jql_query = "project = HPSOFT AND fixVersion = \"rhp-cs5800aw-ref|0.49.0-124decc4\" and updated < 1d"
# jql_query = "project = HPSOFT AND fixVersion = \"rhp-cs5800aw-ref|0.49.0-124decc4\" AND id in (HPSOFT-18652)"
fix_version_to_remove = "rhp-cs5800aw-ref|0.49.0-124decc4"

logger.info(f"Fetching issues with JQL: {jql_query}")
issues = jiraHandler.get_issues(jql_query)

if not issues:
    logger.warning("No issues found matching the criteria")
else:
    logger.info(f"Found {len(issues)} issues to process")
    
    # Use rich's track for better progress display
    for issue in track(issues, description="[cyan]Processing issues..."):
        # Display issue information with rich styling
        console.print(f"\n[bold blue]{issue.key}[/bold blue]: [green]{issue.fields.summary}[/green]")
        
        # Check if issue has the fix version we're looking for
        has_fix_version = False
        for version in issue.fields.fixVersions:
            if version.name == fix_version_to_remove:
                has_fix_version = True
                break
        
        if has_fix_version:
            console.print(f"[yellow]Issue {issue.key} has fix version '{fix_version_to_remove}'[/yellow]")
            
            # Always attempt removal - let the removal method handle different approaches
            jiraHandler.issue_remove_fix_version(issue, fix_version_to_remove)
        else:
            console.print(f"[dim]Issue {issue.key} does NOT have fix version '{fix_version_to_remove}'[/dim]")

logger.success("Script execution completed")
