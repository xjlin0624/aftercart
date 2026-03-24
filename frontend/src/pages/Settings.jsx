import React from "react";
import { settingsAccount } from "../mockData";

export default function Settings() {
  return (
    <div className="page-content">
      <div className="settings-tabs">
        <button className="pill-tab active">Account</button>
        <button className="pill-tab">Notifications</button>
        <button className="pill-tab">Preferences</button>
      </div>

      <div className="settings-card">
        <div className="section-card-title">Account Information</div>

        <div className="settings-grid two-col">
          <div className="form-group">
            <label>First Name</label>
            <input value={settingsAccount.firstName} readOnly />
          </div>

          <div className="form-group">
            <label>Last Name</label>
            <input value={settingsAccount.lastName} readOnly />
          </div>
        </div>

        <div className="settings-grid one-col">
          <div className="form-group">
            <label>Email</label>
            <input value={settingsAccount.email} readOnly />
          </div>
        </div>

        <div className="settings-divider"></div>

        <div className="section-card-title">Change Password</div>

        <div className="settings-grid one-col">
          <div className="form-group">
            <label>Current Password</label>
            <input type="password" />
          </div>
          <div className="form-group">
            <label>New Password</label>
            <input type="password" />
          </div>
          <div className="form-group">
            <label>Confirm New Password</label>
            <input type="password" />
          </div>
        </div>

        <div className="settings-divider"></div>

        <div className="settings-actions">
          <button className="secondary-btn">Cancel</button>
          <button className="primary-btn">Save Changes</button>
        </div>
      </div>
    </div>
  );
}